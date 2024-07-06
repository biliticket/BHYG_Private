# Copyright (c) 2023-2024 ZianTT, FriendshipEnder
import inquirer
import requests
from loguru import logger

from noneprompt import ListPrompt, Choice, InputPrompt

import sentry_sdk

from utils import prompt, save, check_policy

from i18n import *

from globals import *


def utility(config):
    import base64

    def bw_2024(config):
        check_policy(config["uid"])
        load_mode = ListPrompt(
            i18n_format("load_mode"),
            choices=[
                Choice(i18n_format("load_config"), data="read"),
                Choice(i18n_format("new_config"), data="new"),
            ]
        ).prompt().data
        if load_mode == "read":
            logger.info(i18n_format("load_config"))
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    task = json.load(f)
            else:
                logger.info(i18n_format("no_config"))
                task = []
        else:
            logger.info(i18n_format("new_config"))
            task = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Cookie": config["cookie"]
        }
        csrf = headers["Cookie"][
                    headers["Cookie"].index("bili_jct") + 9 : headers["Cookie"].index(
                        "bili_jct"
                    )
                    + 41
                ]
        isbind = requests.get("https://api.bilibili.com/x/activity/bws/online/park/ticket/check", headers=headers).json()["data"]["is_bind"]
        if not isbind:
            logger.info(i18n_format("not_bind"))
            return utility(config)
        info = requests.get("https://api.bilibili.com/x/activity/bws/online/park/reserve/info", headers=headers).json()
        ticket = [None, None, None]
        list = [None, None, None]
        if "20240712" in info["data"]["user_ticket_info"]:
            ticket[0] = {
                "ticket_id": info["data"]["user_ticket_info"]["20240712"]["ticket"],
                "type": info["data"]["user_ticket_info"]["20240712"]["type"],
                "sku_name": "7.12"+info["data"]["user_ticket_info"]["20240712"]["sku_name"],
                "index": 0
            }
            list[0] = info["data"]["reserve_list"]["20240712"]
        if "20240713" in info["data"]["user_ticket_info"]:
            ticket[1] = {
                "ticket_id": info["data"]["user_ticket_info"]["20240713"]["ticket"],
                "type": info["data"]["user_ticket_info"]["20240713"]["type"],
                "sku_name": "7.13"+info["data"]["user_ticket_info"]["20240713"]["sku_name"],
                "index": 1
            }
            list[1] = info["data"]["reserve_list"]["20240713"]
        if "20240714" in info["data"]["user_ticket_info"]:
            ticket[2] = {
                "ticket_id": info["data"]["user_ticket_info"]["20240714"]["ticket"],
                "type": info["data"]["user_ticket_info"]["20240714"]["type"],
                "sku_name": "7.14"+info["data"]["user_ticket_info"]["20240714"]["sku_name"],
                "index": 2
            }
            list[2] = info["data"]["reserve_list"]["20240714"]
        if ticket == [None, None, None]:
            logger.info("没票玩你妈逼")
            return utility(config)
        if task == []:
            while True:
                choices = [
                        Choice(
                            f"{i['ticket_id']}. {i['sku_name']}" if i is not None else "无票，不支持选择",
                            data = i
                        ) for i in ticket
                    ]
                choices.append(Choice("返回", data="back"))
                
                result: Choice[str] = ListPrompt(
                    "选择票时间",
                    choices=choices,
                ).prompt()
                if result.data == "back":
                    break
                if result.data is None:
                    logger.info("无票，不支持选择")
                    continue
                once_ticket_id = result.data["ticket_id"]
                once_index = result.data["index"]

                result: Choice[str] = ListPrompt(
                    "选择预约内容",
                    choices=[
                        Choice(
                            f"{list[once_index][i]["act_title"]} {"VIP" if list[once_index][i]["is_vip_ticket"] else ""} {time.strftime("%m-%d %H:%M", time.localtime(list[once_index][i]["reserve_begin_time"]))}",
                            data = list[once_index][i]
                        ) for i in range(len(list[once_index]))
                    ],
                ).prompt()
                task_detail = result.data
                task_detail["ticket_id"] = once_ticket_id
                task.append(task_detail)

            task.sort(key=lambda x: x["reserve_begin_time"])
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(task, f)
        for i in task:
            while time.time() < i["reserve_begin_time"]-1000000:
                time.sleep(1)
                logger.info("等待中，距离预约时间还有", i["reserve_begin_time"] - time.time(), "秒")
            while True:
                reserve = requests.post("https://api.bilibili.com/x/activity/bws/online/park/reserve/do", headers=headers, data=
                                        {
                                            "csrf": csrf,
                                            "ticket_no": i["ticket_id"],
                                            "inter_reserve_id": i["reserve_id"],
                                        }
                                        )
                if reserve.json()["code"] == 0:
                    logger.info("预约成功")
                    break
                elif reserve.json()["code"] == 412:
                    logger.info("预约失败，重试412")
                elif reserve.json()["code"] == 429:
                    logger.info("预约失败，重试429")
                elif reserve.json()["code"] == -702:
                    logger.info("请求频率过高，请稍后再试")
                elif reserve.json()["code"] == -75574:
                    logger.info("没了")
                    break
                elif reserve.json()["code"] == -76647:
                    logger.info("上限了")
                    break
                elif reserve.json()["code"] == -76650:
                    logger.info("操作频繁")
                else:
                    logger.info(f"{reserve.json()['code']} {reserve.json()['message']}")
                time.sleep(0.95)
        return utility(config)

    def add_buyer(headers):
        name = input(i18n_format("buyer_name"))
        id_type = prompt(
            [
                inquirer.List(
                    "id_type",
                    message=i18n_format("id_type"),
                    choices=[
                        i18n_format("id_idcard"),
                        i18n_format("id_passport"),
                        i18n_format("id_Hong_Kong"),
                        i18n_format("id_Taiwan"),
                    ],
                    default=i18n_format("id_idcard"),
                ),
            ]
        )
        personal_id = input(i18n_format("in_id_serial_number"))
        tel = input(i18n_format("in_phone_number"))
        data = {
            "name": name,
            "tel": tel,
            "id_type": id_type["id_type"].split(".")[0],
            "personal_id": personal_id,
            "is_default": "0",
            "src": "ticket",
        }
        logger.debug(data)
        response = requests.post(
            "https://show.bilibili.com/api/ticket/buyer/create",
            headers=headers,
            data=data,
        )
        if response.json()["errno"] == 0:
            logger.info(i18n_format("join_success"))
        else:
            logger.error(f"{response.json()['errno']}: {response.json()['msg']}")
            return add_buyer(headers)

    def modify_ua():
        ua = input(i18n_format("modify_ua"))
        config["ua"] = ua

    def modify_gaia_vtoken():
        gaia_vtoken = input(i18n_format("modify_gaia_vtoken"))
        config["gaia_vtoken"] = gaia_vtoken

    def hunter_mode():
        config["hunter"] = 0
        logger.info(i18n_format("hunter_mode_on"))

    def hunter_mode_off():
        if "hunter" in config:
            config.pop("hunter")
        logger.info(i18n_format("hunter_mode_off"))

    def share_mode(config):
        import json

        json.dump(config, open("share.json", "w"))
        import os

        os.remove("data")
        logger.info(i18n_format("share_mode"))
        logger.info(i18n_format("auto_quit"))
        import sys

        sys.exit(0)
        return

    def pushplus_config(config):
        token = input(i18n_format("pushplus_token"))
        if token == "":
            if "pushplus" in config:
                config.pop("pushplus")
            logger.info(i18n_format("pushplus_off"))
            save(config)
            return
        config["pushplus"] = token
        logger.info(i18n_format("pushplus_on"))
        save(config)

    def webhook_config(config):
        webhook = input(i18n_format("webhook"))
        if webhook == "":
            if "webhook" in config:
                config.pop("webhook")
            logger.info(i18n_format("webhook_off"))
            save(config)
            return
        config["webhook"] = webhook
        logger.info(i18n_format("webhook_on"))
        save(config)

    def save_phone(config):
        phone = input(i18n_format("input_your_phone"))
        config["phone"] = phone
        logger.info(i18n_format("save_your_phone"))
        save(config)

    def set_offset(config):
        offset = input(i18n_format("input_offset"))
        if offset == "":
            if "time_offset" in config:
                config.pop("time_offset")
            if "cover_time_offset" in config:
                config.pop("cover_time_offset")
            logger.info(i18n_format("offset_off"))
            save(config)
        else:
            config["time_offset"] = float(offset)
            config["cover_time_offset"] = True
            logger.info(i18n_format("save_offset"))
            save(config)

    def use_proxy(config):
        choice = prompt(
            [
                inquirer.List(
                    "proxy",
                    message=i18n_format("input_is_use_proxy"),
                    choices=[i18n_format("yes"), i18n_format("no")],
                    default=i18n_format("no"),
                )
            ]
        )["proxy"]
        if choice == i18n_format("yes"):
            while True:
                try:
                    config["proxy_auth"] = input(i18n_format("input_proxy")).split(" ")
                    assert len(config["proxy_auth"]) == 3
                    break
                except:
                    logger.error(i18n_format("wrong_proxy_format"))
                    continue
            config["proxy_channel"] = prompt(
                [
                    inquirer.Text(
                        "proxy_channel",
                        message=i18n_format("input_proxy_channel"),
                        validate=lambda _, x: x.isdigit(),
                    )
                ]
            )["proxy_channel"]
            config["proxy"] = True
        else:
            config["proxy"] = False
        save(config)

    def captcha_mode(config):
        choice = prompt(
            [
                inquirer.List(
                    "captcha",
                    message=i18n_format("input_use_captcha_mode"),
                    choices=[
                        i18n_format("local_gt"),
                        i18n_format("rrocr"),
                        i18n_format("manual"),
                    ],
                    default=i18n_format("local_gt"),
                )
            ]
        )["captcha"]
        if choice == i18n_format("local_gt"):
            config["captcha"] = "local_gt"
            sentry_sdk.set_tag("captcha", "local_gt")
        elif choice == i18n_format("rrocr"):
            config["captcha"] = "rrocr"
            while True:
                config["rrocr"] = input(i18n_format("input_rrocr_key"))
                if config["rrocr"] != "":
                    break
            sentry_sdk.set_tag("captcha", "rrocr")
        elif choice == i18n_format("manual"):
            config["captcha"] = "manual"
            sentry_sdk.set_tag("captcha", "manual")
        else:
            logger.error(i18n_format("captcha_mode_not_supported"))
        save(config)

    import random

    headers = {
        "Cookie": config["cookie"],
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/618.1.15.10.15 (KHTML, like Gecko) Mobile/21F90 BiliApp/77900100 os/ios model/iPhone 15 mobi_app/iphone build/77900100 osVer/17.5.1 network/2 channel/AppStore c_locale/zh-Hans_CN s_locale/zh-Hans_CH disable_rcmd/0 "
        + str(random.randint(0, 9999)),
        "Referer": "https://show.bilibili.com",
    }
    select = prompt(
        [
            inquirer.List(
                "select",
                message=i18n_format("select_tool"),
                choices=[
                    i18n_format("tool_add_buyer"),
                    i18n_format("tool_modify_ua"),
                    i18n_format("tool_modify_gaia"),
                    i18n_format("tool_hunter_mode"),
                    i18n_format("tool_hunter_off"),
                    i18n_format("tool_share_mode"),
                    i18n_format("tool_pushplus"),
                    i18n_format("tool_phone_prefill"),
                    i18n_format("tool_proxy_setting"),
                    i18n_format("tool_capacha_mode"),
                    i18n_format("tool_webhook"),
                    i18n_format("tool_set_offset"),
                    i18n_format("tool_hide_module"),
                    i18n_format("back"),
                ],
            )
        ]
    )
    if select["select"] == i18n_format("tool_add_buyer"):
        add_buyer(headers)
        return utility(config)
    elif select["select"] == i18n_format("tool_modify_ua"):
        modify_ua()
        return utility(config)
    elif select["select"] == i18n_format("tool_modify_gaia"):
        modify_gaia_vtoken()
        return utility(config)
    elif select["select"] == i18n_format("tool_hunter_mode"):
        hunter_mode()
        return utility(config)
    elif select["select"] == i18n_format("tool_hunter_off"):
        hunter_mode_off()
        return utility(config)
    elif select["select"] == i18n_format("tool_share_mode"):
        share_mode(config)
        return utility(config)
    elif select["select"] == i18n_format("tool_pushplus"):
        pushplus_config(config)
        return utility(config)
    elif select["select"] == i18n_format("tool_phone_prefill"):
        save_phone(config)
        return utility(config)
    elif select["select"] == i18n_format("tool_proxy_setting"):
        use_proxy(config)
        return utility(config)
    elif select["select"] == i18n_format("tool_capacha_mode"):
        captcha_mode(config)
        return utility(config)
    elif select["select"] == i18n_format("tool_webhook"):
        webhook_config(config)
        return utility(config)
    elif select["select"] == i18n_format("tool_set_offset"):
        set_offset(config)
        return utility(config)
    elif select["select"] == i18n_format("back"):
        return
    elif select["select"] == i18n_format("tool_hide_module"):
        name = InputPrompt(i18n_format("input_hide_tool")).prompt()
        if name == "bw_2024":
            bw_2024(config)
        else:
            logger.error(i18n_format("tool_not_supported"))
        return utility()
