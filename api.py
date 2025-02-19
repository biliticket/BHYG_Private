from io import BytesIO
import json
import random
import time
import urllib.parse
import hashlib
import hmac
import secrets
from PIL import Image, ImageDraw

import qrcode
import requests
from loguru import logger
from push import PUSH
from i18n import *

from utils import save, load
from globals import *


class BilibiliHyg:
    global sdk

    def __init__(self, config, sdk):
        self.common_project_id = [
            {"name": "上海·TOGENASHI TOGEARI Live「凛音の理」", "id": 94306},
        ]
        self.waited = True
        self.sdk = sdk
        self.config = config
        self.push_self=PUSH(config)
        self.config["gaia_vtoken"] = None
        self.session = requests.Session()
        if "user-agent" in self.config:
            self.headers = {
                "User-Agent": self.config["user-agent"],
            }
        else:
            self.headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 15;; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/132.0.6834.163 Mobile Safari/537.36 os/android model/BHYG66 build/8300300 osVer/15 sdkInt/35 network/1 BiliApp/8300300 mobi_app/android channel/master Buvid/XUB12BCB16D20812E103A164ED829711BA789 sessionID/27d578d0 innerVer/8300310 c_locale/zh_CN s_locale/zh_CN disable_rcmd/0 themeId/2 sh/40",
            }
        self.headers["Cookie"] = self.config["cookie"]
        
        # 模式选择逻辑区
        if "mode" not in config:
            try:
                mode_str = (
                    noneprompt.ListPrompt(
                        question=i18n_format("choose_mode"),
                        choices=[
                            noneprompt.Choice(name=i18n_format(x), data=x)
                            for x in ["mode_time", "mode_direct", "mode_detect"]
                        ],
                    )
                    .prompt()
                    .data
                )
            except noneprompt.CancelledError as e:
                return
            if mode_str == "mode_direct":
                config["mode"] = "direct"
                logger.info(i18n_format("mode_direct_on"))
            elif mode_str == "mode_detect":
                config["mode"] = "detect"
                logger.info(i18n_format("mode_detect_on"))
            else:
                config["mode"] = "time"
                logger.info(i18n_format("mode_time_on"))

        # 检测模式: 票务信息获取延迟设置区
        if "status_delay" not in config and config["mode"] == "detect":
            while True:
                try:
                    config["status_delay"] = noneprompt.InputPrompt(
                        question=i18n_format("input_status_delay")
                    ).prompt(default="0.2")
                except noneprompt.CancelledError:
                    logger.info(i18n_format("cancelled"))
                    return
                if config["status_delay"] == "":
                    config["status_delay"] = 0.2
                try:
                    config["status_delay"] = float(config["status_delay"])
                    if config["status_delay"] < 0:
                        raise ValueError
                    break
                except ValueError:
                    logger.error(i18n_format("wrong_input"))

        # 下单请求延迟设置区

        if "co_delay" not in config:
            while True:
                config["co_delay"] = noneprompt.InputPrompt(
                    question=i18n_format("input_co_delay"),
                    default_text="0",
                ).prompt(default="0")
                if config["co_delay"] == "":
                    config["co_delay"] = 0
                try:
                    config["co_delay"] = float(config["co_delay"])
                    if config["co_delay"] < 0:
                        raise ValueError
                    break
                except ValueError:
                    logger.error(i18n_format("wrong_input"))

        # 验证码模式设置区
        if "captcha" not in config:
            logger.info(i18n_format("captcha_mode_gt_by_default"))
            config["captcha"] = "local_gt"
        if config["captcha"] == "local_gt":
            logger.info(i18n_format("captcha_mode_gt"))
        elif config["captcha"] == "manual":
            logger.info(i18n_format("captcha_mode_manual"))
        else:
            logger.error(i18n_format("captcha_mode_not_supported"))
            return

        # 场次选择区
        if (
            "project_id" not in config
            or "screen_id" not in config
            or "sku_id" not in config
            or "pay_money" not in config
            or "id_bind" not in config
        ):
            while not self.select_screen():
                pass

        # 购买人信息获取区
        while not self.select_buyer_info():
            pass

        self.config = config
        save(self.config)
        logger.debug(config)

        if self.config["mode"] == "time":
            logger.info(i18n_format("now_mode_time_on"))
            logger.info(i18n_format("wait_get_token"))
            while self.get_time() < self.config["time"] - 60:
                time.sleep(10)
                logger.info(
                    i18n_format("now_waiting_info").format(
                        (self.config["time"] - self.get_time())
                    )
                )
            while self.get_time() < self.config["time"]:
                pass
        logger.info(i18n_format("get_token_finish"))
        self.token = self.get_token()
        logger.info(i18n_format("will_pay_bill"))


    # 选座主逻辑
    # 传出 True/False 代表选择是否成功，若False考虑重新选择
    def pick_seat(self):
        area_info = self.session.get(
           "https://show.bilibili.com/api/ticket/place/get",
           params={
              "project_id": self.config["project_id"],
              "screen_id": self.config["screen_id"],
              "timestamp": int(time.time() * 1000),
           },
           headers=self.headers,
        )
        if area_info.status_code == 412:
            logger.error(i18n_format("not_handled_412"))
            return False
        area_info = area_info.json()
        base_pic = self.session.get(
           "https:"+area_info["data"]["base_pic"], headers=self.headers
        ).content
        im = Image.open(BytesIO(base_pic))
        im = im.resize((area_info["data"]["d_width"], area_info["data"]["d_height"]))
        draw = ImageDraw.Draw(im)
        area_list = area_info["data"]["area_list"]
        colors = [
           (255, 0, 0), # 红色
           (0, 255, 0), # 绿色
           (0, 0, 255), # 蓝色
           (255, 255, 0), # 黄色
        ]
        color_name = [
           "area_red",
           "area_green",
           "area_blue",
           "area_yellow",
        ]
        for area_id in area_info["data"]["available_area"]:
            points = area_list[str(area_id)].split(",")
            for i in range(0, len(points)):
                start_point_x, start_point_y = points[i].split(" ")
                end_point_x, end_point_y = points[(i + 1) % len(points)].split(" ")
                draw.line(
                   (
                      int(start_point_x),
                      int(start_point_y),
                      int(end_point_x),
                      int(end_point_y),
                   ),
                   fill=colors[area_id % len(colors)],
                   width=5,
                )
        im.show()
        
        selected_seats = []
        while True:
            area_id = (
                        noneprompt.ListPrompt(
                            question=i18n_format("show_area_info"),
                            choices=[
                                noneprompt.Choice(name=i18n_format("show_area").format(
                                    area_id,
                                    area_info["data"]["area_name"][str(area_id)],
                                    i18n_format(color_name[area_id % len(colors)]), 
                                )
                                , data=area_id) for area_id in area_info["data"]["available_area"]
                            ],
                        )
                        .prompt()
                        .data
                    )
            seats = self.session.get(
            "https://show.bilibili.com/api/ticket/area/seat",
            params={
                "screen_id": self.config["screen_id"],
                "area_id": area_id,
                "timestamp": int(time.time() * 1000), 
            },
            headers=self.headers
            )
            if seats.status_code == 412:
                logger.error(i18n_format("not_handled_412"))
                return False
            seats = seats.json()
            max_limit = seats["data"]["max_limit"]
            seat_list = seats["data"]["seats"]
            seatsName = seats["data"]["seatsName"]
            symbol = seats["data"]["symbol"]
            unavailable_seats = seats["data"]["unavailable"]
            for seat in unavailable_seats:
                seat_list[int(seat.split('_')[0])] = seat_list[int(seat.split('_')[0])][:int(seat.split('_')[1])] + "X" + seat_list[int(seat.split('_')[0])][int(seat.split('_')[1])+1:]
            for seat in selected_seats:
                if int(seat.split('_')[0]) == int(area_id):
                    seat_list[int(seat.split('_')[1])] = seat_list[int(seat.split('_')[1])][:int(seat.split('_')[2])] + "O" + seat_list[int(seat.split('_')[1])][int(seat.split('_')[2])+1:]
            print("X\\Y ", end="")
            line_len = len(seat_list[0])
            for i in range(0, line_len):
                # print(f"{i%10} ", end="")
                if i < 10:
                    print(f"{i}  ", end="")
                else:
                    print(f"{i} ", end="")
            print()
            for i in range(0, len(seat_list)):
                print(f"{i%10}   ", end="")
                for j in range(0, len(seat_list[i])):
                    if seat_list[i][j] in ["X", "_", "#"]:
                        print(seat_list[i][j], end="  ")
                    elif seat_list[i][j] == "O":
                        print("\033[31m"+seat_list[i][j]+"\033[0m", end="  ")
                    else:
                        print("\033[34m"+seat_list[i][j]+"\033[0m", end="  ")
                print()
            for seat_symbol, seat in symbol.items():
                logger.info(
                    i18n_format("show_seat_info").format(
                        seat_symbol,
                        seat["desc"],
                        seat["price"] / 100,
                        " 售罄" if seat["sale_flag"] == 0 else "",
                    ) 
                )
            select_seat = (
                noneprompt.InputPrompt(
                    i18n_format("input_seat"),
                    validator=lambda x: len(x.split(" ")) == 2 and x.split(" ")[0].isdigit() and x.split(" ")[1].isdigit() or x == "",
                )
               .prompt()
            )
            if select_seat == "":
                break
            if int(select_seat.split(" ")[0]) >= len(seat_list):
                logger.error(i18n_format("seat_not_found"))
                continue
            if int(select_seat.split(" ")[1]) >= len(seat_list[int(select_seat.split(" ")[0])]):
                logger.error(i18n_format("seat_not_found!"))
                continue
            if seat_list[int(select_seat.split(" ")[0])][int(select_seat.split(" ")[1])] == "O":
                logger.error(i18n_format("seat_already_selected"))
                continue
            if seat_list[int(select_seat.split(" ")[0])][int(select_seat.split(" ")[1])] in ["X", "_", "#"]:
                logger.error(i18n_format("seat_not_available"))
                continue
            selected_seats.append(str(area_id)+"_"+select_seat.split(" ")[0]+"_"+select_seat.split(" ")[1])
            logger.info(i18n_format("seat_selected").format(select_seat.split(" ")[0], select_seat.split(" ")[1], seatsName[select_seat.split(" ")[0]+"_"+select_seat.split(" ")[1]]))
            if len(selected_seats) == max_limit:
                break
        self.config["selected_seats"] = selected_seats
        logger.info(i18n_format("seat_selected_finish"))
        # TODO 票务信息计算
        # TODO Prepare逻辑重写
        return True

            


    # 场次选择主逻辑
    # 传出 True/False 代表选择是否成功，若False考虑重新选择
    def select_screen(self):
        logger.info(i18n_format("common_project_id"))
        for i in range(len(self.common_project_id)):
            logger.info(
                self.common_project_id[i]["name"]
                    + " id: "
                    + str(self.common_project_id[i]["id"])
                )
        if len(self.common_project_id) == 0:
            logger.info(i18n_format("empty"))
        self.config["project_id"] = noneprompt.InputPrompt(
            i18n_format("input_project_id"), validator=lambda x: x.isdigit()
        ).prompt(default="0")
        url = (
            "https://show.bilibili.com/api/ticket/project/getV2?id="
            + self.config["project_id"]
        )
        response = self.session.get(url, headers=self.headers)
        
        req_time=time.time()
        if response.status_code == 412:
            logger.error(i18n_format("not_handled_412"))
        response = response.json()
        if response["errno"] == 3:
            logger.error(i18n_format("project_id_not_found"))
            return False
        if response["data"] == {}:
            logger.error(i18n_format("server_no_response"))
            return False
        if "screen_list" not in response["data"]:
            logger.error(i18n_format("no_screen"))
            return False
        if len(response["data"]["screen_list"]) == 0:
            logger.error(i18n_format("no_screen"))
            return False
        logger.info(i18n_format("project_name").format(response["data"]["name"]))
        self.config["id_bind"] = response["data"]["id_bind"]
        self.config["is_pick_seat"]  = response["data"]["pick_seat"]
        # 场次选择区
        screens = response["data"]["screen_list"]
        screen_id = (
            noneprompt.ListPrompt(
                i18n_format("select_screen"),
                choices=[
                    noneprompt.Choice(f"{i}. {screens[i]['name']}", data=i)
                    for i in range(len(screens))
                ],
            )
            .prompt()
            .data
        )
        logger.info(
            i18n_format("show_screen").format(screens[int(screen_id)]["name"])
        )
        tickets = screens[int(screen_id)]["ticket_list"]  # type: ignore
        self.config["screen_id"] = str(screens[int(screen_id)]["id"])
        # 票种选择区
        if self.config["is_pick_seat"]:
            # 选座逻辑区
            while not self.pick_seat():
                pass
        else:
            sku_id = (
                noneprompt.ListPrompt(
                    i18n_format("select_sku"),
                    choices=[
                        noneprompt.Choice(
                            f"{i}. {tickets[i]['desc']} {tickets[i]['price'] / 100}元",
                            data=i,
                        )
                        for i in range(len(tickets))
                    ],
                )
                .prompt()
                .data
            )
            logger.info(i18n_format("show_sku").format(tickets[int(sku_id)]["desc"]))
        # 选择结束，开始整理
        self.config["sku_id"] = str(tickets[int(sku_id)]["id"])
        self.config["pay_money"] = str(tickets[int(sku_id)]["price"])
        self.config["ticket_desc"] = str(tickets[int(sku_id)]["desc"])
        self.config["is_paper_ticket"] = screens[int(screen_id)]["delivery_type"] != 1
        self.config["time"] = int(tickets[int(sku_id)]["saleStart"])-int(response["data"]["current_time"])+req_time
        if tickets[int(sku_id)]["discount_act"] is not None:
            logger.info(
                i18n_format("show_act").format(
                    tickets[int(sku_id)]["discount_act"]["act_id"]
                    )
            )
            self.config["act_id"] = tickets[int(sku_id)]["discount_act"]["act_id"]
            self.config["order_type"] = tickets[int(sku_id)]["discount_act"]["act_type"]
        else:
            self.config["order_type"] = "1"
        if self.config["is_paper_ticket"]:
            if screens[int(screen_id)]["express_free_flag"]:
                self.config["express_fee"] = 0
            else:
                self.config["express_fee"] = screens[int(screen_id)]["express_fee"]
            url = "https://show.bilibili.com/api/ticket/addr/list"
            resp_ticket = self.session.get(url, headers=self.headers)
            if resp_ticket.status_code == 412:
                logger.error(i18n_format("not_handled_412"))
            addr_list = resp_ticket.json()["data"]["addr_list"]
            if len(addr_list) == 0:
                logger.error(i18n_format("add_address"))
            else:
                addr = addr_list[
                    noneprompt.ListPrompt(
                        question=i18n_format("please_select_address"),
                        choices=[
                            noneprompt.Choice(
                                name=f"{i}. {addr_list[i]['prov'] + addr_list[i]['city'] + addr_list[i]['area'] + addr_list[i]['addr']} {addr_list[i]['name']} {addr_list[i]['phone']}",
                                    data=i,
                            )
                            for i in range(len(addr_list))
                        ],
                    )
                    .prompt().data
                    ]
                logger.info(
                    i18n_format("already_select_address").format(
                        addr["prov"] + addr["city"] + addr["area"] + addr["addr"],
                        addr["name"],
                        addr["phone"],
                    )
                )
                self.config["deliver_info"] = json.dumps(
                    {
                        "name": addr["name"],
                        "tel": addr["phone"],
                        "addr_id": addr["addr"],
                        "addr": addr["prov"] + addr["city"] + addr["area"] + addr["addr"],
                        },
                        ensure_ascii=False,
                    )
        logger.debug(
                f"您的screen_id 和 sku_id 和 pay_money 分别为：{self.config["screen_id"]} {self.config["sku_id"]} {self.config["pay_money"]}"
        )
        logger.debug(f"您的开始销售时间为：{self.config['time']}")
        return True
    
    # 身份信息逻辑区
    def select_buyer_info(self):
        match self.config["id_bind"]:
            case 0:
                if "buyer" in self.config and "tel" in self.config:
                    return True
                else:
                    logger.info(i18n_format("add_contact_info"))
                    try:
                        self.config["buyer"] = noneprompt.InputPrompt(
                            question=i18n_format("add_contact_name")
                        ).prompt()
                        self.config["tel"] = noneprompt.InputPrompt(
                            question=i18n_format("add_contact_tel"),
                            validator=lambda x: len(x) == 11,
                        ).prompt()
                    except noneprompt.CancelledError as e:
                        raise KeyboardInterrupt("Cancelled by user") from e
                    if "phone" not in self.config or self.config["phone"] == "":  # 如果未预约填写手机号
                        self.config["phone"] = self.config[
                            "tel"
                        ]  # 自动保存填写的手机号(这种票应该用不到手机号验证吧)
                        logger.info(
                            i18n_format("auto_save_phone").format(  # 用作预填手机号
                                self.config["phone"][:3], self.config["phone"][-4:]
                            )  # 可用于手机号短信验证
                        )  # 小影 2024.7.6
                    else:  # 目前问题就是能通过cookie
                        logger.info(
                            i18n_format("already_save_phone").format(  # 获取账号绑定的手机号
                                self.config["phone"][:3], self.config["phone"][-4:]
                            )  # 这样就更完美了
                        )
                    if "count" not in self.config:
                        self.config["count"] = noneprompt.InputPrompt(
                            question=i18n_format("add_buy_tickets"),
                            default_text="1",
                            validator=lambda x: x.isdigit() and int(x) > 0,
                        ).prompt()
            case 1 | 2:
                if "buyer_info" in self.config:
                    return True
                url = "https://show.bilibili.com/api/ticket/buyer/list"
                response = self.session.get(url, headers=self.headers)
                if response.status_code == 412:
                    logger.error(i18n_format("not_handled_412"))
                buyer_infos = response.json()["data"]["list"]
                self.config["buyer_info"] = []
                if len(buyer_infos) == 0:
                    logger.error(i18n_format("buyer_empty"))
                    return False
                multiselect = True if self.config["id_bind"] == 2 else False
                if multiselect:
                    buyers = noneprompt.CheckboxPrompt(
                        i18n_format("select_buyer"),
                        choices=[
                            noneprompt.Choice(
                                f"{i['name'][0] + '*' * (len(i['name']) - 2) + i['name'][-1]} {i['personal_id'][:4] + '**********' + i['personal_id'][-4:]} {i['tel'][:3] + '****' + i['tel'][-4:]}",
                                data=i,
                            )
                            for i in buyer_infos
                        ],
                        validator=lambda x: len(x) > 0,
                    ).prompt()
                    self.config["buyer_info"] = []
                    for select in buyers:
                        self.config["buyer_info"].append(select.data)
                        logger.info(
                            i18n_format("selected_buyer").format(
                                select.data["name"][0]
                                + "*" * (len(select.data["name"]) - 2)
                                + select.data["name"][-1],
                                select.data["personal_id"][:4]
                                + "**********"
                                + select.data["personal_id"][-4:],
                                select.data["tel"][:3] + "****" + select.data["tel"][-4:],
                            )
                        )
                    if (
                        "phone" not in self.config or self.config["phone"] == ""
                    ):  # 如果未预约填写手机号
                        self.config["phone"] = buyer_infos[0][
                            "tel"
                        ]  # 自动保存默认购票人的手机号
                        logger.info(
                            i18n_format("auto_save_phone").format(  # 用作预填手机号
                                self.config["phone"][:3], self.config["phone"][-4:]
                            )  # 可用于手机号短信验证
                        )  # 小影 2024.7.6
                    else:  # 目前问题就是能通过cookie
                        logger.info(
                            i18n_format(
                                "already_save_phone"
                            ).format(  # 获取账号绑定的手机号
                                self.config["phone"][:3], self.config["phone"][-4:]
                            )  # 这样就更完美了 @@ZianTT
                        )
                else:
                    index = noneprompt.ListPrompt(
                        question=i18n_format("select_buyer"),
                        choices=[
                            noneprompt.Choice(
                                f"{i['name'][0] + '*' * (len(i['name']) - 2) + i['name'][-1]} {i['personal_id'][:4] + '**********' + i['personal_id'][-4:]} {i['tel'][:3] + '****' + i['tel'][-4:]}",
                                data=i,
                            )
                            for i in buyer_infos
                        ],
                    ).prompt()
                    self.config["buyer_info"].append(index.data)
                    logger.debug(index.data)
                    logger.info(
                            i18n_format("selected_buyer").format(
                                index.data["name"][0]
                                + "*" * (len(index.data["name"]) - 2)
                                + index.data["name"][-1],
                                index.data["personal_id"][:4]
                                + "**********"
                                + index.data["personal_id"][-4:],
                                index.data["tel"][:3]
                                + "****"
                                + index.data["tel"][-4:],
                            )
                        )
                    if (
                        "phone" not in self.config or self.config["phone"] == ""
                    ):  # 如果未预约填写手机号
                        self.config["phone"] = buyer_infos[0][
                            "tel"
                        ]  # 自动保存默认购票人的手机号
                        logger.info(
                            i18n_format("auto_save_phone").format(  # 用作预填手机号
                                self.config["phone"][:3], self.config["phone"][-4:]
                            )  # 可用于手机号短信验证
                        )  # 小影 2024.7.6
                    else:  # 目前问题就是能通过cookie
                        logger.info(
                            i18n_format(
                                "already_save_phone"
                            ).format(  # 获取账号绑定的手机号
                                self.config["phone"][:3], self.config["phone"][-4:]
                            )  # 这样就更完美了
                        )
                if "count" not in self.config:
                    self.config["count"] = len(self.config["buyer_info"])
                self.config["buyer_info"] = json.dumps(self.config["buyer_info"])
                return True
            case _:
                logger.error(i18n_format("id_bind_error"))
                return False

    def get_time(self):
        return float(time.time() + self.config["time_offset"])

    def get_ticket_status(self):
        url = (
            "https://show.bilibili.com/api/ticket/project/getV2?id="
            + self.config["project_id"]
        )
        try:
            response = self.session.get(url, headers=self.headers, timeout=1)
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError,
        ):
            logger.error(i18n_format("network_timeout"))
            return -1, 0
        try:
            if response.status_code == 412:
                logger.error(i18n_format("wind_control"))
                self.risk = True
                logger.error(i18n_format("net_method"))
                try:
                    if noneprompt.ConfirmPrompt(
                        question=i18n_format("res_return")
                    ).prompt():
                        return -1, 0
                except noneprompt.CancelledError:
                    return -1, 0
            screens = response.json()["data"]["screen_list"]
            # 找到 字段id为screen_id的screen
            screen = {}
            for i in range(len(screens)):
                if screens[i]["id"] == int(self.config["screen_id"]):
                    screen = screens[i]
                    break
            if screen == {}:
                logger.error(i18n_format("no_found_screen"))
                return -1, 0
            # 找到 字段id为sku_id的sku
            skus = screen["ticket_list"]
            sku = {}
            for i in range(len(skus)):
                if skus[i]["id"] == int(self.config["sku_id"]):
                    sku = skus[i]
                    break
            if sku == {}:
                logger.error(i18n_format("no_found_sku"))
                return -1, 0
            return int(sku["sale_flag_number"]), sku["clickable"]
        except:
            logger.error(i18n_format("may_wind_control"))
            return -1, 0

    def get_prepare(self):
        url = (
            "https://show.bilibili.com/api/ticket/order/prepare?project_id="
            + self.config["project_id"]
        )
        if self.config["gaia_vtoken"]:
            url += "&gaia_vtoken=" + self.config["gaia_vtoken"]
        data = {
            "project_id": self.config["project_id"],
            "screen_id": self.config["screen_id"],
            "order_type": self.config["order_type"],
            "count": self.config["count"],
            "token": "",
            "newRisk": "true",
            "ignoreRequestLimit": "true",
            "requestSource": "neul-next",
        }
        if self.config["is_select_seat"]:
            data["seats"] = self.config["selected_seats"]
        else:
            data["sku_id"] = self.config["sku_id"]
        if "act_id" in self.config:
            data["act_id"] = self.config["act_id"]
        response = self.session.post(url, headers=self.headers, data=data)
        if response.status_code == 412:
            logger.error(i18n_format("not_handled_412"))
        if response.json()["errno"] != 0 and response.json()["errno"] != -401:
            logger.error(response.json()["msg"])
        return response.json()["data"]

    def gee_verify(self, gt, challenge, token):
        from geetest import run

        time_start = time.time()
        if "key" in self.config:
            self.captcha_data = run(
                gt,
                challenge,
                token,
                mode=self.config["captcha"],
            )
        else:
            self.captcha_data = run(gt, challenge, token, mode=self.config["captcha"])
        delta = time.time() - time_start
        self.sdk.metrics.distribution(
            key="gt_solve_time", value=delta * 1000, unit="millisecond"
        )
        self.captcha_data["csrf"] = self.headers["Cookie"][
            self.headers["Cookie"].index("bili_jct") + 9 : self.headers["Cookie"].index(
                "bili_jct"
            )
            + 41
        ]
        self.captcha_data["token"] = token
        success = self.session.post(
            "https://api.bilibili.com/x/gaia-vgate/v1/validate",
            headers=self.headers,
            data=self.captcha_data,
        ).json()
        try:
            assert success["data"]["is_valid"] == True
            success = True
        except:
            success = False
        self.config["gaia_vtoken"] = token
        self.captcha_data = None
        if self.headers["Cookie"].find("x-bili-gaia-vtoken") != -1:
            self.headers["Cookie"] = self.headers["Cookie"].split(
                "; x-bili-gaia-vtoken"
            )[0]
        self.headers["Cookie"] += "; x-bili-gaia-vtoken=" + token
        save(self.config)
        return success

    def phone_verify(self, token):
        if "phone" in self.config:
            phone = self.config["phone"]
        else:
            try:
                phone = noneprompt.InputPrompt(
                    question=i18n_format("input_phone_num"),
                    validator=lambda x: x.isdigit(),
                ).prompt()
            except noneprompt.CancelledError:
                return False
        self.captcha_data = {
            "code": phone,
        }
        self.captcha_data["csrf"] = self.headers["Cookie"][
            self.headers["Cookie"].index("bili_jct") + 9 : self.headers["Cookie"].index(
                "bili_jct"
            )
            + 41
        ]
        self.captcha_data["token"] = token
        success = self.session.post(
            "https://api.bilibili.com/x/gaia-vgate/v1/validate",
            headers=self.headers,
            data=self.captcha_data,
        ).json()
        try:
            assert success["data"]["is_valid"] == True
            success = True
        except:
            success = False
        if not success:
            logger.error(i18n_format("input_verify_fail"))
            if "phone" in self.config:
                self.config.pop("phone")
            return False
        self.config["gaia_vtoken"] = token
        self.captcha_data = None
        if self.headers["Cookie"].find("x-bili-gaia-vtoken") != -1:
            self.headers["Cookie"] = self.headers["Cookie"].split(
                "; x-bili-gaia-vtoken"
            )[0]
        self.headers["Cookie"] += "; x-bili-gaia-vtoken=" + token
        save(self.config)
        return success

    def confirm_info(self, token):
        url = (
            "https://show.bilibili.com/api/ticket/order/confirmInfo?token="
            + token
            + "&timestamp="
            + str(int(time.time() * 1000))
            + "&project_id="
            + self.config["project_id"]
            + "&requestSource=neul-next"
        )
        response = self.session.get(url, headers=self.headers)
        if response.status_code == 412:
            logger.error(i18n_format("not_handled_412"))
        response = response.json()
        logger.info(i18n_format("info_confirmed"))
        logger.debug(response)
        self.config["order_type"] = response["data"]["order_type"]
        if response["data"]["act"] is not None:
            logger.info(i18n_format("info_discount"))
            self.config["act_id"] = response["data"]["act"]["act_id"]
        self.config["count"] = response["data"]["count"]
        self.config["all_price"] = response["data"]["pay_money"]
        return

    def get_token(self):
        info = self.get_prepare()
        if info == {}:
            logger.warning(i18n_format("info_no_ticket"))
            time.sleep(2)
            return self.get_token()
        if info["token"]:
            if self.config["is_select_seat"]:
                if info["failed_seats"] != []:
                    logger.warning(
                        i18n_format("info_some_seat_fail")
                    )
            logger.success(
                i18n_format("info_bill_ok")
                + "https://show.bilibili.com/platform/confirmOrder.html?token="
                + info["token"]
            )
            self.sdk.add_breadcrumb(
                category="prepare",
                message=f'Order prepared as token:{info["token"]}',
                level="info",
            )
            try:
                self.confirm_info(info["token"])
            except:
                logger.error(i18n_format("info_bill_fail"))
                return self.get_token()
            return info["token"]
        else:
            logger.warning(i18n_format("info_wind_control"))
            self.sdk.add_breadcrumb(
                category="gaia",
                message="Gaia found",
                level="info",
            )
            riskParam = info["ga_data"]["riskParams"]
            # https://api.bilibili.com/x/gaia-vgate/v1/register
            risk = self.session.post(
                "https://api.bilibili.com/x/gaia-vgate/v1/register",
                headers=self.headers,
                data=riskParam,
            ).json()
            while risk["code"] != 0:
                risk = self.session.post(
                    "https://api.bilibili.com/x/gaia-vgate/v1/register",
                    headers=self.headers,
                    data=riskParam,
                ).json()
            if risk["data"]["type"] == "geetest":
                logger.warning(i18n_format("type_captcha"))
                gt, challenge, token = (
                    risk["data"]["geetest"]["gt"],
                    risk["data"]["geetest"]["challenge"],
                    risk["data"]["token"],
                )
                cap_data = self.gee_verify(gt, challenge, token)
                while cap_data == False:
                    logger.error(i18n_format("input_verify_fail"))
                    return self.get_token()
                logger.info(i18n_format("input_verify_success"))
            elif risk["data"]["type"] == "phone":
                logger.warning(i18n_format("type_mobile"))
                token = risk["data"]["token"]
                cap_data = self.phone_verify(token)
                while cap_data == False:
                    logger.error(i18n_format("input_verify_fail"))
                    return self.get_token()
            elif risk["data"]["type"] == "sms":
                logger.warning(i18n_format("type_sms"))
                logger.warning(i18n_format("unsupport_sms"))
            elif risk["data"]["type"] == "biliword":
                logger.warning(i18n_format("type_sms"))
                logger.warning(i18n_format("unsupport_text"))
            else:
                logger.error(i18n_format("unknown_wind"))
                logger.warning(i18n_format("unsupport_captcha"))
            self.sdk.add_breadcrumb(
                category="gaia",
                message="Gaia passed",
                level="info",
            )
            return self.get_token()

    def generate_clickPosition(self) -> dict:
        """
        生成虚假的点击事件

        Returns:
            dict: 点击坐标和时间
        """
        # 生成随机的 x 和 y 坐标，以下范围大概是1920x1080屏幕下可能的坐标
        x = random.randint(1320, 1330)
        y = random.randint(880, 890)
        # 生成随机的起始时间和结束时间（或当前时间）
        now_timestamp = int(time.time() * 1000)
        # 添加一些随机时间差 (5s ~ 10s)
        origin_timestamp = now_timestamp - random.randint(5000, 10000)
        return {"x": x, "y": y, "origin": origin_timestamp, "now": now_timestamp}

    def create_order(self):
        url = "https://show.bilibili.com/api/ticket/order/createV2"
        data = {
            "project_id": self.config["project_id"],
            "screen_id": self.config["screen_id"],
            "token": self.token,
            "deviceId": secrets.token_hex(),
            "project_id": self.config["project_id"],
            "pay_money": self.config["all_price"],
            "count": self.config["count"],
            "timestamp": int(time.time()*1000),
            "newRisk": "true",
            "requestSource": "neul-next",
            "clickPosition": self.generate_clickPosition(),
        }
        if self.config["is_select_seat"]:
            data["seats"] = self.config["selected_seats"]
        else:
            data["sku_id"] = self.config["sku_id"]
        if "super" not in self.config:
            data["order_type"] = (self.config["order_type"],)
        if self.config["id_bind"] == 0:
            data["buyer"] = self.config["buyer"]
            data["tel"] = self.config["tel"]
        else:
            data["buyer_info"] = self.config["buyer_info"]
        if self.config["is_paper_ticket"]:
            data["deliver_info"] = self.config["deliver_info"]
        if "act_id" in self.config:
            data["act_id"] = self.config["act_id"]
        data["again"] = 1

        try:
            response = self.session.post(url, headers=self.headers, data=data)
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError,
        ):
            logger.error(i18n_format("network_timeout"))
            return self.create_order()
        if response.status_code == 412:
            logger.error(i18n_format("wind_control"))
            self.risk = True
            logger.error(i18n_format("pause_60s"))
            time.sleep(60)
            return {}
        return response.json()

    def fake_ticket(self, pay_token, order_id=None):
        url = (
            "https://show.bilibili.com/api/ticket/order/createstatus?project_id="
            + self.config["project_id"]
            + "&token="
            + pay_token
            + "&timestamp="
            + str(int(time.time() * 1000))
        )
        if order_id:
            url += "&orderId=" + str(order_id)
        logger.debug(url)
        response = self.session.get(url, headers=self.headers)
        if response.status_code == 412:
            logger.error(i18n_format("not_handled_412"))
        response = response.json()
        logger.debug(response)
        if response["errno"] == 0:
            self.sdk.add_breadcrumb(
                category="success",
                message=f'Success, orderid:{response["data"]["order_id"]}, payurl:https://pay.bilibili.com/payplatform-h5/pccashier.html?params="{urllib.parse.quote(json.dumps(response["data"]["payParam"], ensure_ascii=False))}',
                level="info",
            )
            logger.success(i18n_format("pay_success"))
            order_id = response["data"]["order_id"]
            pay_url = response["data"]["payParam"]["code_url"]
            response["data"]["payParam"].pop("code_url")
            response["data"]["payParam"].pop("expire_time")
            response["data"]["payParam"].pop("pay_type")
            response["data"]["payParam"].pop("use_huabei")
            logger.info(i18n_format("bill_serial") + order_id)
            self.order_id = order_id
            logger.info(i18n_format("bill_pay_hint"))
            logger.info(i18n_format("bill_qr") + pay_url)
            PUSH.push(self.push_self,i18n_format("bill_qr") + pay_url)
            qr = qrcode.QRCode()
            qr.add_data(pay_url)
            qr.print_ascii(invert=True)
            img = qr.make_image()
            img.show()
            logger.info(
                i18n_format("bill_open")
                + " https://pay.bilibili.com/payplatform-h5/pccashier.html?params="
                + urllib.parse.quote(
                    json.dumps(response["data"]["payParam"], ensure_ascii=False)
                )
                + " "
                + i18n_format("bill_pay_ok")
            )
            logger.info(i18n_format("bill_manual"))
            return True
        else:
            logger.error(i18n_format("bill_fail"))
            return False

    def order_status(self, order_id):
        url = "https://show.bilibili.com/api/ticket/order/info?order_id=" + str(
            order_id
        )
        response = self.session.get(url, headers=self.headers)
        if response.status_code == 412:
            logger.error(i18n_format("not_handled_412"))
        response = response.json()
        if response["data"]["status"] == 1:
            return True
        elif response["data"]["status"] == 2:
            logger.success(i18n_format("pay_ok"))
            return False
        elif response["data"]["status"] == 4:
            logger.warning(i18n_format("bill_cancel"))
            return False
        else:
            logger.warning(
                i18n_format("status_unknown")
                + ": "
                + response["data"]["status_name"]
                + response["data"]["sub_status_name"]
            )
            return False
        
    def reselect(self):
        # TODO: 座位被占用
        pass

    def logout(self):
        # https://passport.bilibili.com/login/exit/v2
        url = "https://passport.bilibili.com/login/exit/v2"
        # biliCSRF	str	CSRF Token (位于 cookie 中的 bili_jct)
        response = self.session.post(
            url,
            headers=self.headers,
            data={
                "biliCSRF": self.headers["Cookie"][
                    self.headers["Cookie"].index("bili_jct") + 9 : self.headers[
                        "Cookie"
                    ].index("bili_jct")
                    + 41
                ]
            },
        ).json()
        if response["status"] == True:
            logger.success(i18n_format("quit_login"))
        else:
            logger.error(i18n_format("logout_fail"))

    def try_create_order(self):
        time.sleep(self.config["co_delay"])
        if not self.waited:
            if "super" not in self.config:
                logger.info(i18n_format("wait_4_96s"))
                time.sleep(4.96)
            elif "super_delay" in self.config:
                time.sleep(self.config["super_delay"])
            self.waited = True
        result = self.create_order()
        logger.debug(result)
        if result == {}:
            return False
        if result["errno"] == 100009:
            logger.warning(i18n_format("ticketless"))
            self.waited = False
        elif result["errno"] == 100017:
            logger.warning(i18n_format("ticket_unbuyable"))
            self.waited = False
        elif result["errno"] == 3:
            logger.warning(i18n_format("slowdown_5s"))
        elif result["errno"] == 100001:
            logger.warning(i18n_format("bili_speed_limit"))
        elif result["errno"] == 100041:
            logger.warning(i18n_format("tokenless"))
        elif result["errno"] == 100016:
            logger.error(i18n_format("not_salable"))
        elif result["errno"] == 101006:
            self.reselect_seat()
            self.waited = False
        elif result["errno"] == 0:
            logger.success(i18n_format("bill_push_ok"))
            pay_token = result["data"]["token"]
            orderid = None
            if "orderId" in result["data"]:
                orderid = result["data"]["orderId"]
            if self.fake_ticket(pay_token, order_id=orderid):
                self.sdk.capture_message("Get order!")
                # self.logout()
                PUSH.push(self.push_self,i18n_format("pay_success"))
                logger.info(i18n_format("unpaid_bill"))
                while self.order_status(self.order_id):
                    time.sleep(2)
                self.sdk.capture_message("Exit by in-app exit")
                return True
            else:
                logger.error(i18n_format("fake_ticket"))
        elif result["errno"] == 100051 or result["errno"] == 100050:
            while True:
                try:
                    self.token = self.get_token()
                    break
                except:
                    pass
        elif result["errno"] == 100079 or result["errno"] == 100048:
            logger.info(result["msg"])
            logger.success(i18n_format("rob_already_ok"))
            self.sdk.capture_message("Exit by in-app exit")
            return True
        elif result["errno"] == 219:
            logger.info(i18n_format("ticket_sto_less"))
            self.sold_out = True
        else:
            logger.error(i18n_format("unknown_error") + str(result))
        return False

    @staticmethod
    def gen_bili_ticket():
        def hmac_sha256(key, message):
            """
            使用HMAC-SHA256算法对给定的消息进行加密
            :param key: 密钥
            :param message: 要加密的消息
            :return: 加密后的哈希值
            """
            key = key.encode("utf-8")
            message = message.encode("utf-8")
            hmac_obj = hmac.new(key, message, hashlib.sha256)
            hash_value = hmac_obj.digest()
            hash_hex = hash_value.hex()
            return hash_hex

        o = hmac_sha256("XgwSnGZ1p", f"ts{int(time.time())}")
        url = (
            "https://api.bilibili.com/bapis/bilibili.api.ticket.v1.Ticket/GenWebTicket"
        )
        params = {
            "key_id": "ec02",
            "hexsign": o,
            "context[ts]": f"{int(time.time())}",
            "csrf": "",
        }

        import random

        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/618.1.15.10.15 (KHTML, like Gecko) Mobile/21F90 BiliApp/77900100 os/ios model/iPhone 15 mobi_app/iphone build/77900100 osVer/17.5.1 network/2 channel/AppStore c_locale/zh-Hans_CN s_locale/zh-Hans_CH disable_rcmd/0 "
            + str(random.randint(0, 9999)),
        }
        resp = requests.post(url, params=params, headers=headers).json()
        return resp["data"]["ticket"]
