# -*- coding: UTF-8 -*-
# Copyright (c) 2023-2024 ZianTT, FriendshipEnder
import json
import os
import threading
import time

import kdl

import noneprompt

import requests
from loguru import logger

from api import BilibiliHyg
from globals import *

from utils import save, load, check_policy

import noneprompt

from i18n import *

common_project_id = [
    {"name": "上海·BilibiliWorld 2024", "id": 85939},
    {"name": "上海·BILIBILI MACRO LINK 2024", "id": 85938},
]


def run(hyg):
    if "super" in hyg.config:
        logger.info(i18n_format("super_mode_on_msg"))
    if hyg.config["mode"] == "direct" or hyg.config["mode"] == "time":
        while True:
            if hyg.try_create_order():
                if "hunter" not in hyg.config:
                    hyg.sdk.capture_message("Pay success!")
                    logger.success(i18n_format("pay_success"))
                    return
                else:
                    hyg.config["hunter"] += 1
                    save(hyg.config)
                    logger.success(
                        i18n_format("hunter_prompt").format(hyg.config["hunter"])
                    )
    elif hyg.config["mode"] == "detect":
        token_time = time.time()
        while 1:
            if time.time() - token_time > 300:
                token_time = time.time()
                hyg.get_token()
            hyg.risk = False
            if hyg.risk:
                status = -1
            status, clickable = hyg.get_ticket_status()
            if status == 2 or clickable:
                logger.info(i18n_format("begin_buy"))
                if status == 1:
                    logger.warning(i18n_format("not_begin"))
                elif status == 3:
                    logger.warning(i18n_format("has_end_buy"))
                elif status == 5:
                    logger.warning(i18n_format("cannot_buy"))
                elif status == 102:
                    logger.warning(i18n_format("has_end"))
                start_time = time.time()
                hyg.sold_out = False
                while time.time() - start_time < 20 and not hyg.sold_out:
                    if hyg.try_create_order():
                        if "hunter" not in hyg.config:
                            hyg.sdk.capture_message("Pay success!")
                            logger.success(i18n_format("pay_success"))
                            return
                        else:
                            hyg.config["hunter"] += 1
                            save(hyg.config)
                            logger.success(
                                i18n_format("hunter_prompt").format(
                                    hyg.config["hunter"]
                                )
                            )
                        break
            elif status == 1:
                logger.warning(i18n_format("not_begin"))
            elif status == 3:
                logger.warning(i18n_format("has_end_buy"))
            elif status == 4:
                logger.warning(i18n_format("sold_out"))
            elif status == 5:
                logger.warning(i18n_format("cannot_buy"))
            elif status == 8:
                logger.warning(i18n_format("pro_tem_sold_out"))
            elif status == 6:
                logger.error(i18n_format("free_not_supported"))
                sentry_sdk.capture_message("Exit by in-app exit")
                return

            elif status == -1:
                continue
            else:
                logger.error(i18n_format("unk_status") + str(status))
            time.sleep(hyg.config["status_delay"])


def main():
    #    easter_egg = False
    #    user_male = False
    #    user_female = False
    from globals import version

    set_language(False)
    print(i18n_format("start_up").format(version))
    global kdl_client
    kdl_client = None
    try:
        sentry_sdk = init(version)
        session = requests.session()

        check_key = check_policy()
        logger.info(i18n_format("tips"))
        config = load_config()
        if config == None:
            return
        if check_key:
            check_policy(uid=config["uid"])
        import random

        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/618.1.15.10.15 (KHTML, like Gecko) Mobile/21F90 BiliApp/77900100 os/ios model/iPhone 15 mobi_app/iphone build/77900100 osVer/17.5.1 network/2 channel/AppStore c_locale/zh-Hans_CN s_locale/zh-Hans_CH disable_rcmd/0 "
            + str(random.randint(0, 9999)),
            "Cookie": config["cookie"],
        }
        if "user-agent" in config:
            headers["User-Agent"] = config["user-agent"]
        session = requests.Session()
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
                raise KeyboardInterrupt("Cancelled by user") from e
            if mode_str == "mode_direct":
                config["mode"] = "direct"
                logger.info(i18n_format("mode_direct_on"))
            elif mode_str == "mode_detect":
                config["mode"] = "detect"
                logger.info(i18n_format("mode_detect_on"))
            else:
                config["mode"] = "time"
                logger.info(i18n_format("mode_time_on"))
        if "status_delay" not in config and config["mode"] == "detect":
            while True:
                config["status_delay"] = noneprompt.InputPrompt(
                    question=i18n_format("input_status_delay")
                ).prompt(default="0.2")
                if config["status_delay"] == "":
                    config["status_delay"] = 0.2
                try:
                    config["status_delay"] = float(config["status_delay"])
                    if config["status_delay"] < 0:
                        raise ValueError
                    break
                except ValueError:
                    logger.error(i18n_format("wrong_input"))
        if "proxy" not in config:
            logger.info(i18n_format("no_proxy_by_default"))
            config["proxy"] = False
        if "captcha" not in config:
            logger.info(i18n_format("captcha_mode_gt_by_default"))
            config["captcha"] = "local_gt"
        if "rrocr" not in config:
            config["rrocr"] = None
        if config["captcha"] == "local_gt":
            logger.info(i18n_format("captcha_mode_gt"))
        elif config["captcha"] == "rrocr":
            logger.info(i18n_format("captcha_mode_rrocr"))
        elif config["captcha"] == "manual":
            logger.info(i18n_format("captcha_mode_manual"))
        else:
            logger.error(i18n_format("captcha_mode_not_supported"))
            return
        if config["proxy"] == True:
            auth = kdl.Auth(config["proxy_auth"][0], config["proxy_auth"][1])
            kdl_client = kdl.Client(auth)
            session.proxies = {
                "http": config["proxy_auth"][2],
                "https": config["proxy_auth"][2],
            }
            if config["proxy_channel"] != "0":
                headers["kdl-tps-channel"] = config["proxy_channel"]
            session.keep_alive = False
            session.get("https://show.bilibili.com")
            logger.info(
                i18n_format("test_proxy").format(
                    kdl_client.tps_current_ip(sign_type="hmacsha1")
                )
            )
        if (
            "project_id" not in config
            or "screen_id" not in config
            or "sku_id" not in config
            or "pay_money" not in config
            or "id_bind" not in config
        ):
            while True:
                logger.info(i18n_format("common_project_id"))
                for i in range(len(common_project_id)):
                    logger.info(
                        common_project_id[i]["name"]
                        + " id: "
                        + str(common_project_id[i]["id"])
                    )
                if len(common_project_id) == 0:
                    logger.info(i18n_format("empty"))
                config["project_id"] = noneprompt.InputPrompt(
                    i18n_format("input_project_id"), validator=lambda x: x.isdigit()
                ).prompt(default="0")
                url = (
                    "https://show.bilibili.com/api/ticket/project/getV2?version=134&id="
                    + config["project_id"]
                )
                response = session.get(url, headers=headers)
                if response.status_code == 412:
                    logger.error(i18n_format("not_handled_412"))
                    if config["proxy"]:
                        logger.info(
                            i18n_format("manual_change_ip").format(
                                kdl_client.change_tps_ip(sign_type="hmacsha1")
                            )
                        )
                        session.close()
                response = response.json()
                if response["errno"] == 3:
                    logger.error(i18n_format("project_id_not_found"))
                    continue
                if response["data"] == {}:
                    logger.error(i18n_format("server_no_response"))
                    continue
                if "screen_list" not in response["data"]:
                    logger.error(i18n_format("no_screen"))
                    continue
                if len(response["data"]["screen_list"]) == 0:
                    logger.error(i18n_format("no_screen"))
                    continue
                break
            logger.info(i18n_format("project_name").format(response["data"]["name"]))
            config["id_bind"] = response["data"]["id_bind"]
            config["is_paper_ticket"] = response["data"]["has_paper_ticket"]
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
            config["screen_id"] = str(screens[int(screen_id)]["id"])
            config["sku_id"] = str(tickets[int(sku_id)]["id"])
            config["pay_money"] = str(tickets[int(sku_id)]["price"])
            config["ticket_desc"] = str(tickets[int(sku_id)]["desc"])
            config["time"] = int(tickets[int(sku_id)]["saleStart"])
            if tickets[int(sku_id)]["discount_act"] is not None:
                logger.info(
                    i18n_format("show_act").format(
                        tickets[int(sku_id)]["discount_act"]["act_id"]
                    )
                )
                config["act_id"] = tickets[int(sku_id)]["discount_act"]["act_id"]
                config["order_type"] = tickets[int(sku_id)]["discount_act"]["act_type"]
            else:
                config["order_type"] = "1"
            if config["is_paper_ticket"]:
                if response["data"]["express_free_flag"]:
                    config["express_fee"] = 0
                else:
                    config["express_fee"] = response["data"]["express_fee"]
                url = "https://show.bilibili.com/api/ticket/addr/list"
                resp_ticket = session.get(url, headers=headers)
                if resp_ticket.status_code == 412:
                    logger.error(i18n_format("not_handled_412"))
                    if config["proxy"]:
                        logger.info(
                            i18n_format("manual_change_ip").format(
                                kdl_client.change_tps_ip(sign_type="hmacsha1")
                            )
                        )
                        session.close()
                addr_list = resp_ticket.json()["data"]["addr_list"]
                if len(addr_list) == 0:
                    logger.error(i18n_format("add_address"))
                else:
                    addr = addr_list[
                        (
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
                            .prompt()
                            .data
                        )
                    ]
                    logger.info(
                        i18n_format("already_select_address").format(
                            addr["prov"] + addr["city"] + addr["area"] + addr["addr"],
                            addr["name"],
                            addr["phone"],
                        )
                    )
                    config["deliver_info"] = json.dumps(
                        {
                            "name": addr["name"],
                            "tel": addr["phone"],
                            "addr_id": addr["addr"],
                            "addr": addr["prov"]
                            + addr["city"]
                            + addr["area"]
                            + addr["addr"],
                        },
                        ensure_ascii=False,
                    )
            logger.debug(
                "您的screen_id 和 sku_id 和 pay_money 分别为："
                + config["screen_id"]
                + " "
                + config["sku_id"]
                + " "
                + config["pay_money"]
            )
            logger.debug("您的开始销售时间为：" + str(config["time"]))
        if config["id_bind"] != 0 and ("buyer_info" not in config):
            url = "https://show.bilibili.com/api/ticket/buyer/list"
            response = session.get(url, headers=headers)
            if response.status_code == 412:
                logger.error(i18n_format("not_handled_412"))
            buyer_infos = response.json()["data"]["list"]
            config["buyer_info"] = []
            if len(buyer_infos) == 0:
                logger.error(i18n_format("buyer_empty"))
                return
            else:
                multiselect = True
            if config["id_bind"] == 1:
                logger.info(i18n_format("id_bind_single"))
                multiselect = False
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
                config["buyer_info"] = []
                for select in buyers:
                    config["buyer_info"].append(select.data)
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
                    "phone" not in config or config["phone"] == ""
                ):  # 如果未预约填写手机号
                    config["phone"] = buyer_infos[0][
                        "tel"
                    ]  # 自动保存默认购票人的手机号
                    logger.info(
                        i18n_format("auto_save_phone").format(  # 用作预填手机号
                            config["phone"][:3], config["phone"][-4:]
                        )  # 可用于手机号短信验证
                    )  # 小影 2024.7.6
                else:  # 目前问题就是能通过cookie
                    logger.info(
                        i18n_format(
                            "already_save_phone"
                        ).format(  # 获取账号绑定的手机号
                            config["phone"][:3], config["phone"][-4:]
                        )  # 这样就更完美了 @@ZianTT
                    )
            #                    if int(buyer_infos[int(select)]["personal_id"][16]) % 2 == 0:
            #                        user_female = True
            #                    else:
            #                        user_male = True
            #                if easter_egg:
            #                    if len(buyerids) == 1:
            #                        logger.info("单身是这样的🤣 情(xiàn)侣(chōng)们只需要相互做搭子就可以逛的很开心, 可是一个人去逛漫展的人们需要考虑的事情就多了。")
            #                    else:
            #                        if user_male and user_female:
            #                            logger.error("小情侣不得house😡")
            #                        elif user_male and not user_female:
            #                            logger.error("我朝，有南通啊！")
            #                            if len(buyerids) == 4:
            #                                logger.error("我朝，开impart啊！")
            #                        elif user_female and not user_male:
            #                            logger.error("我朝，有女同啊！")
            else:
                index = noneprompt.CheckboxPrompt(
                    question=i18n_format("select_buyer"),
                    choices=[
                        noneprompt.Choice(
                            name="{}. {} {} {}".format(
                                i,
                                buyer_infos[i]["name"][0]
                                + "*" * (len(buyer_infos[i]["name"]) - 2)
                                + buyer_infos[i]["name"][-1],
                                buyer_infos[i]["personal_id"][:4]
                                + "**********"
                                + buyer_infos[i]["personal_id"][-4:],
                                buyer_infos[i]["tel"][:3]
                                + "****"
                                + buyer_infos[i]["tel"][-4:],
                            ),
                            data=i,
                        )
                    ],
                ).prompt()
                config["buyer_info"].append(buyer_infos[i.data] for i in index)
                logger.info(
                    i18n_format("selected_buyer").format(
                        buyer_infos[int(index.split(".")[0])]["name"][0]
                        + "*" * (len(buyer_infos[int(index.split(".")[0])]["name"]) - 2)
                        + buyer_infos[int(index.split(".")[0])]["name"][-1],
                        buyer_infos[int(index.split(".")[0])]["personal_id"][:4]
                        + "**********"
                        + buyer_infos[int(index.split(".")[0])]["personal_id"][-4:],
                        buyer_infos[int(index.split(".")[0])]["tel"][:3]
                        + "****"
                        + buyer_infos[int(index.split(".")[0])]["tel"][-4:],
                    )
                )
                if (
                    "phone" not in config or config["phone"] == ""
                ):  # 如果未预约填写手机号
                    config["phone"] = buyer_infos[0][
                        "tel"
                    ]  # 自动保存默认购票人的手机号
                    logger.info(
                        i18n_format("auto_save_phone").format(  # 用作预填手机号
                            config["phone"][:3], config["phone"][-4:]
                        )  # 可用于手机号短信验证
                    )  # 小影 2024.7.6
                else:  # 目前问题就是能通过cookie
                    logger.info(
                        i18n_format(
                            "already_save_phone"
                        ).format(  # 获取账号绑定的手机号
                            config["phone"][:3], config["phone"][-4:]
                        )  # 这样就更完美了
                    )
            if "count" not in config:
                config["count"] = len(config["buyer_info"])
            config["buyer_info"] = json.dumps(config["buyer_info"])
        if config["id_bind"] == 0 and ("buyer" not in config or "tel" not in config):
            logger.info(i18n_format("add_contact_info"))
            try:
                config["buyer"] = noneprompt.InputPrompt(
                    question=i18n_format("add_contact_name")
                ).prompt()
                config["tel"] = noneprompt.InputPrompt(
                    question=i18n_format("add_contact_tel"),
                    validator=lambda x: len(x) == 11,
                ).prompt()
            except noneprompt.CancelledError as e:
                raise KeyboardInterrupt("Cancelled by user") from e
            if "phone" not in config or config["phone"] == "":  # 如果未预约填写手机号
                config["phone"] = config[
                    "tel"
                ]  # 自动保存填写的手机号(这种票应该用不到手机号验证吧)
                logger.info(
                    i18n_format("auto_save_phone").format(  # 用作预填手机号
                        config["phone"][:3], config["phone"][-4:]
                    )  # 可用于手机号短信验证
                )  # 小影 2024.7.6
            else:  # 目前问题就是能通过cookie
                logger.info(
                    i18n_format("already_save_phone").format(  # 获取账号绑定的手机号
                        config["phone"][:3], config["phone"][-4:]
                    )  # 这样就更完美了
                )
            if "count" not in config:
                config["count"] = noneprompt.InputPrompt(
                    question=i18n_format("add_buy_tickets"),
                    default_text="1",
                    validator=lambda x: x.isdigit() and int(x) > 0,
                ).prompt()
        if config["is_paper_ticket"]:
            if config["express_fee"] == 0:
                config["all_price"] = int(config["pay_money"]) * int(config["count"])
                logger.info(
                    i18n_format("show_all_price_paper_ticket").format(
                        config["count"],
                        config["ticket_desc"],
                        int(config["pay_money"]) / 100,
                        0,
                        config["all_price"] / 100,
                    )
                )
            else:
                config["all_price"] = (
                    int(config["pay_money"]) * int(config["count"])
                    + config["express_fee"]
                )
                logger.info(
                    i18n_format("show_all_price_paper_ticket").format(
                        config["count"],
                        config["ticket_desc"],
                        int(config["pay_money"]) / 100,
                        config["express_fee"] / 100,
                        config["all_price"] / 100,
                    )
                )
        else:
            config["all_price"] = int(config["pay_money"]) * int(config["count"])
            logger.info(
                i18n_format("show_all_price_e_ticket").format(
                    config["count"],
                    config["ticket_desc"],
                    int(config["pay_money"]) / 100,
                    config["all_price"] / 100,
                )
            )
        save(config)
        sentry_sdk.set_context("config", config)
        sentry_sdk.capture_message("config complete")
        BHYG = BilibiliHyg(config, sentry_sdk, kdl_client, session)
        BHYG.waited = True
        run(BHYG)
    except KeyboardInterrupt:
        logger.info(i18n_format("exit_manual"))
        return
    except Exception as e:
        track = sentry_sdk.capture_exception(e)
        logger.error(i18n_format("error_occured").format(str(e), str(track)))
        return
    return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info(i18n_format("exit_manual"))
    from sentry_sdk import Hub

    client = Hub.current.client
    if client is not None:
        client.close(timeout=2.0)
    logger.info(i18n_format("exit_sleep_15s"))
    try:
        time.sleep(15)
    except KeyboardInterrupt:
        pass
