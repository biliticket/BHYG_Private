# Copyright (c) 2023-2024 ZianTT, FriendshipEnder
from logging import log
from os import pathsep
import requests

import noneprompt

import sentry_sdk
import pyperclip

from utils import save, check_policy

from i18n import *

from globals import *


def utility(config):
    import base64

    def super(config):
        check_policy(uid=config["uid"], res="super")
        if "super" in config:
            config.pop("super")
            logger.info(i18n_format("super_mode_off"))
        else:
            config["super"] = True
            try:
                super_delay = noneprompt.InputPrompt(
                    i18n_format("super_delay"),
                    validator=lambda x: x.replace(".", "", 1).isdigit(),
                ).prompt()
                config["super_delay"] = float(super_delay)
            except noneprompt.CancelledError:
                logger.info(i18n_format("cancelled"))
                return
            logger.info(i18n_format("super_mode_on"))
        save(config)
        return

    def bw_2024(config):
        check_policy(uid=config["uid"], res="bw_2024")
        load_mode = (
            noneprompt.ListPrompt(
                i18n_format("load_mode"),
                choices=[
                    noneprompt.Choice(i18n_format("load_config"), data="read"),
                    noneprompt.Choice(i18n_format("new_config"), data="new"),
                ],
            )
            .prompt()
            .data
        )
        if load_mode == "read":
            logger.info(i18n_format("load_config"))
            if os.path.exists("task.json"):
                with open("task.json", "r", encoding="utf-8") as f:
                    task = json.load(f)
            else:
                logger.info(i18n_format("no_config"))
                task = []
        else:
            logger.info(i18n_format("new_config"))
            task = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Cookie": config["cookie"],
        }
        csrf = headers["Cookie"][
            headers["Cookie"].index("bili_jct") + 9 : headers["Cookie"].index(
                "bili_jct"
            )
            + 41
        ]
        isbind = requests.get(
            "https://api.bilibili.com/x/activity/bws/online/park/ticket/check",
            headers=headers,
        ).json()["data"]["is_bind"]
        if not isbind:
            logger.info(i18n_format("not_bind"))
            return
        info = requests.get(
            "https://api.bilibili.com/x/activity/bws/online/park/reserve/info?reserve_date=20240712,20240713,20240714",
            headers=headers,
        ).json()
        ticket = [None, None, None]
        list = [None, None, None]
        logger.debug(json.dumps(info["data"]["reserve_list"]))
        if "20240712" in info["data"]["user_ticket_info"]:
            ticket[0] = {
                "ticket_id": info["data"]["user_ticket_info"]["20240712"]["ticket"],
                "type": info["data"]["user_ticket_info"]["20240712"]["type"],
                "sku_name": "7.12"
                + info["data"]["user_ticket_info"]["20240712"]["sku_name"],
                "index": 0,
            }
            list[0] = info["data"]["reserve_list"]["20240712"]
        if "20240713" in info["data"]["user_ticket_info"]:
            ticket[1] = {
                "ticket_id": info["data"]["user_ticket_info"]["20240713"]["ticket"],
                "type": info["data"]["user_ticket_info"]["20240713"]["type"],
                "sku_name": "7.13"
                + info["data"]["user_ticket_info"]["20240713"]["sku_name"],
                "index": 1,
            }
            list[1] = info["data"]["reserve_list"]["20240713"]
        if "20240714" in info["data"]["user_ticket_info"]:
            ticket[2] = {
                "ticket_id": info["data"]["user_ticket_info"]["20240714"]["ticket"],
                "type": info["data"]["user_ticket_info"]["20240714"]["type"],
                "sku_name": "7.14"
                + info["data"]["user_ticket_info"]["20240714"]["sku_name"],
                "index": 2,
            }
            list[2] = info["data"]["reserve_list"]["20240714"]
        if ticket == [None, None, None]:
            logger.info("没票玩你妈逼")
            return
        if task == []:
            while True:
                noneprompt.Choices = [
                    noneprompt.Choice(
                        f"{i['ticket_id']}. {i['sku_name']}"
                        if i is not None
                        else "无票，不支持选择",
                        data=i,
                    )
                    for i in ticket
                ]
                noneprompt.Choices.append(noneprompt.Choice("返回", data="back"))

                result: noneprompt.Choice[str] = noneprompt.ListPrompt(
                    "选择票时间",
                    choices=noneprompt.Choices,
                ).prompt()
                if result.data == "back":
                    break
                if result.data is None:
                    logger.info("无票，不支持选择")
                    continue
                once_ticket_id = result.data["ticket_id"]
                once_index = result.data["index"]

                result: noneprompt.Choice[str] = noneprompt.ListPrompt(
                    "选择预约内容",
                    choices=[
                        noneprompt.Choice(
                            f"{list[once_index][i]['act_title']} {'VIP场次(非VIP票请勿选择)' if list[once_index][i]['is_vip_ticket'] else ''} {time.strftime('%m-%d %H:%M', time.localtime(list[once_index][i]['reserve_begin_time']))}",
                            data=list[once_index][i],
                        )
                        for i in range(len(list[once_index]))
                    ],
                ).prompt()
                task_detail = result.data
                task_detail["ticket_id"] = once_ticket_id
                task.append(task_detail)

            task.sort(key=lambda x: x["reserve_begin_time"])
            with open("task.json", "w", encoding="utf-8") as f:
                json.dump(task, f)
        for i in task:
            logger.info(
                f"{i['screen_date']} {i['act_title']} {time.strftime('%m-%d %H:%M', time.localtime(i['reserve_begin_time']))}"
            )
        for i in task:
            while time.time() < i["reserve_begin_time"] - 5:
                time.sleep(1)
                logger.info(
                    f"等待中，距离预约时间还有{i['reserve_begin_time'] - time.time()}秒(提前5s开始尝试预约)"
                )
            while True:
                reserve = requests.post(
                    "https://api.bilibili.com/x/activity/bws/online/park/reserve/do",
                    headers=headers,
                    data={
                        "csrf": csrf,
                        "ticket_no": i["ticket_id"],
                        "inter_reserve_id": i["reserve_id"],
                    },
                )
                if reserve.json()["code"] == 0:
                    logger.info("预约成功")
                    sentry_sdk.capture_message("bw_2024")
                    break
                elif reserve.json()["code"] == 412:
                    logger.info("预约失败，重试412")
                elif reserve.json()["code"] == 429:
                    logger.info("预约失败，重试429")
                elif abs(reserve.json()["code"]) == 702:
                    logger.info("请求频率过高，请稍后再试")
                elif abs(reserve.json()["code"]) == 75574:
                    logger.info("没了")
                    break
                elif abs(reserve.json()["code"]) == 76647:
                    logger.info("上限了")
                    break
                elif abs(reserve.json()["code"]) == 76650:
                    logger.info("操作频繁")
                else:
                    logger.info(f"{reserve.json()['code']} {reserve.json()['message']}")
                time.sleep(0.95)
        return

    def add_buyer(headers):
        try:
            name = noneprompt.InputPrompt(question=i18n_format("buyer_name")).prompt()
            id_type = (
                noneprompt.ListPrompt(
                    question=i18n_format("id_type"),
                    choices=[
                        noneprompt.Choice(name=i18n_format(x), data=x)
                        for x in [
                            "id_idcard",
                            "id_passport",
                            "id_Hong_Kong",
                            "id_Taiwan",
                        ]
                    ],
                    default_select=1,
                )
                .prompt()
                .data
            )
            personal_id = noneprompt.InputPrompt(
                question=i18n_format("in_id_serial_number")
            ).prompt()
            tel = noneprompt.InputPrompt(
                question=i18n_format("in_phone_number")
            ).prompt()
        except noneprompt.CancelledError as e:
            raise KeyboardInterrupt("Cancelled by user.") from e
        for i in range(4): #下面传入的id_type
            if id_type == ["id_idcard","id_passport","id_Hong_Kong","id_Taiwan"][i]:
                id_type = i
                break
            
        data = {
            "name": name,
            "tel": tel,
            "id_type": id_type,
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
        ua = noneprompt.InputPrompt(question=i18n_format("modify_ua")).prompt()
        config["ua"] = ua

    def modify_gaia_vtoken():
        gaia_vtoken = noneprompt.InputPrompt(
            question=i18n_format("modify_gaia_vtoken")
        ).prompt()
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
        try:
            try:
                clip_value = pyperclip.paste()
                logger.info(i18n_format("clip_paste_success"))
            except pyperclip.PyperclipException:
                clip_value = ""
            token = noneprompt.InputPrompt(
                question=i18n_format("pushplus_token"),
                default_text=clip_value,
            ).prompt()
        except noneprompt.CancelledError:
            logger.info(i18n_format("cancelled"))
            return
        if token == "":
            if "pushplus_token" in config:
                config.pop("pushplus")
            logger.info(i18n_format("pushplus_off"))
            save(config)
            return
        config["pushplus_token"] = token
        logger.info(i18n_format("pushplus_on"))
        save(config)

    def bark_config(config):
        try:
            try:
                clip_value = pyperclip.paste()
                logger.info(i18n_format("clip_paste_success"))
            except pyperclip.PyperclipException:
                clip_value = ""
            token = noneprompt.InputPrompt(
                question=i18n_format("bark_token"),
                default_text=clip_value,
            ).prompt()
        except noneprompt.CancelledError:
            logger.info(i18n_format("cancelled"))
            return
        if token == "":
            if "bark_token" in config:
                config.pop("bark_token")
            logger.info(i18n_format("bark_off"))
            save(config)
            return
        config["bark_token"] = token
        logger.info(i18n_format("bark_on"))
        save(config)
    def dingding_config(config):
        try:
            try:
                clip_value = pyperclip.paste()
                logger.info(i18n_format("clip_paste_success"))
            except pyperclip.PyperclipException:
                clip_value = ""
            webhook = noneprompt.InputPrompt(
                question=i18n_format("dingding"), default_text=clip_value
            ).prompt()
        except noneprompt.CancelledError:
            logger.info(i18n_format("cancelled"))
            return
        if webhook == "":
            if "dingding_token" in config:
                config.pop("dingding_token")
            logger.info(i18n_format("dingding_off"))
            save(config)
            return
        config["dingding_token"] = webhook
        logger.info(i18n_format("dingding_on"))
        save(config)

    def wx_config(config):
        try:
            try:
                clip_value = pyperclip.paste()
                logger.info(i18n_format("clip_paste_success"))
            except pyperclip.PyperclipException:
                clip_value = ""
            webhook = noneprompt.InputPrompt(
                question=i18n_format("wxpush"), default_text=clip_value
            ).prompt()
        except noneprompt.CancelledError:
            logger.info(i18n_format("cancelled"))
            return
        if webhook == "":
            if "wx_token" in config:
                config.pop("wx_token")
            logger.info(i18n_format("dingding_off"))
            save(config)
            return
        config["wx_token"] = webhook
        logger.info(i18n_format("wxpush_on"))
        save(config)
        
    def ftqq_config(config):
        try:
            try:
                clip_value = pyperclip.paste()
                logger.info(i18n_format("clip_paste_success"))
            except pyperclip.PyperclipException:
                clip_value = ""
            webhook = noneprompt.InputPrompt(
                question=i18n_format("ftqq"), default_text=clip_value
            ).prompt()
        except noneprompt.CancelledError:
            logger.info(i18n_format("cancelled"))
            return
        if webhook == "":
            if "ftqq_token" in config:
                config.pop("ftqq_token")
            logger.info(i18n_format("ftqq_off"))
            save(config)
            return
        config["ftqq_token"] = webhook
        logger.info(i18n_format("ftqq_on"))
        save(config) 

    def smtp_config(config):
        try:
            try:
                clip_value = pyperclip.paste()
                logger.info(i18n_format("clip_paste_success"))
            except pyperclip.PyperclipException:
                clip_value = ""
            smtp_mail_host = noneprompt.InputPrompt(
                question=i18n_format("smtp_mail_host"), default_text=clip_value
            ).prompt()
            smtp_mail_user=noneprompt.InputPrompt(
                question=i18n_format("smtp_mail_user"), default_text=clip_value
            ).prompt()
            smtp_mail_pass=noneprompt.InputPrompt(
                question=i18n_format("smtp_mail_pass"), default_text=clip_value
            ).prompt()
            smtp_sender=noneprompt.InputPrompt(
                question=i18n_format("smtp_sender"), default_text=clip_value
            ).prompt()
            smtp_receivers=noneprompt.InputPrompt(
                question=i18n_format("smtp_receivers"), default_text=clip_value
            ).prompt()  #可传多个收件人，要按照['']格式传进来，如['114514@123.com','141414@123.com']  @violite 24.9.20
        except noneprompt.CancelledError:
            logger.info(i18n_format("cancelled"))
            return
        if not smtp_mail_host and smtp_mail_pass and smtp_sender and smtp_receivers and smtp_mail_user:
            if "smtp_mail_pass" in config:  #太多项目了，偷个懒只检测有没有密码作为开关 @violite 24.9.20
                config.pop("smtp_mail_pass")
            logger.info(i18n_format("smtp_off"))
            save(config)
            return
        config["smtp_mail_host"] = smtp_mail_host
        config["smtp_mail_user"]=smtp_mail_user
        config["smtp_mail_pass"]=smtp_mail_pass
        config["smtp_sender"]=smtp_sender
        config["smtp_receivers"]=list(smtp_receivers.split(","))
        logger.info(i18n_format("smtp_on"))
        save(config)                 
    def save_phone(config):
        try:
            phone = noneprompt.InputPrompt(
                question=i18n_format("input_your_phone"),
                validator=lambda x: x.isdigit(),
            ).prompt()
        except noneprompt.CancelledError as e:
            logger.info(i18n_format("cancelled"))
        config["phone"] = phone
        logger.info(i18n_format("save_your_phone"))
        save(config)

    def set_offset(config):
        try:
            offset = noneprompt.InputPrompt(
                question=i18n_format("input_offset")
            ).prompt()
        except noneprompt.CancelledError:
            logger.info(i18n_format("cancelled"))
            return
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
        try:
            confirm_proxy = noneprompt.ConfirmPrompt(
                question=i18n_format("input_is_use_proxy"),
                default_choice=False,
            ).prompt()
        except noneprompt.CancelledError:
            logger.info(i18n_format("cancelled"))
            return
        if confirm_proxy:
            while True:
                try:
                    try:
                        try:
                            clip_value = pyperclip.paste()
                            logger.info(i18n_format("clip_paste_success"))
                        except pyperclip.PyperclipException:
                            clip_value = ""
                        config["proxy_auth"] = (
                            noneprompt.InputPrompt(
                                question=i18n_format("input_proxy"),
                                default_text=clip_value,
                            )
                            .prompt()
                            .split(" ")
                        )
                    except noneprompt.CancelledError:
                        logger.info(i18n_format("cancelled"))
                        return
                    assert len(config["proxy_auth"]) == 3
                    break
                except:
                    logger.error(i18n_format("wrong_proxy_format"))
                    continue
            try:
                config["proxy_channel"] = noneprompt.InputPrompt(
                    question=i18n_format("input_proxy_channel"),
                    validator=lambda x: x.isdigit(),
                ).prompt()
            except noneprompt.CancelledError:
                logger.info(i18n_format("cancelled"))
                return
            config["proxy"] = True
        else:
            config["proxy"] = False
        save(config)

    def captcha_mode(config):
        try:
            cap_pass = (
                noneprompt.ListPrompt(
                    question=i18n_format("input_use_captcha_mode"),
                    choices=[
                        noneprompt.Choice(name=i18n_format(x), data=x)
                        for x in ["local_gt", "rrocr", "manual"]
                    ],
                )
                .prompt()
                .data
            )
        except noneprompt.CancelledError as e:
            logger.info(i18n_format("cancelled"))
            return
        if cap_pass == "local_gt":
            config["captcha"] = "local_gt"
            sentry_sdk.set_tag("captcha", "local_gt")
        elif cap_pass == "rrocr":
            config["captcha"] = "rrocr"
            while True:
                try:
                    config["rrocr"] = noneprompt.InputPrompt(
                        question=i18n_format("input_rrocr_key")
                    ).prompt()
                except noneprompt.CancelledError:
                    logger.info(i18n_format("cancelled"))
                    return
                if config["rrocr"] != "":
                    break
            sentry_sdk.set_tag("captcha", "rrocr")
        elif cap_pass == "manual":
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
    select = (
        noneprompt.ListPrompt(
            question=i18n_format("select_tool"),
            choices=[
                noneprompt.Choice(i18n_format(x), data=x)
                for x in ["tool_add_buyer", "tool_modify_ua", "tool_modify_gaia", "tool_hunter_mode", "tool_hunter_off", "tool_share_mode", "tool_phone_prefill", "tool_proxy_setting", "tool_capacha_mode","tool_pushplus", "tool_bark","tool_dingding","tool_wx_push","tool_ftqq","tool_smtp", "tool_set_offset", "tool_hide_module", "back",]],
        )
        .prompt()
        .data
    )
    if select == "tool_add_buyer":
        add_buyer(headers)
        return utility(config)
    elif select == "tool_modify_ua":
        modify_ua()
        return utility(config)
    elif select == "tool_modify_gaia":
        modify_gaia_vtoken()
        return utility(config)
    elif select == "tool_hunter_mode":
        hunter_mode()
        return utility(config)
    elif select == "tool_hunter_off":
        hunter_mode_off()
        return utility(config)
    elif select == "tool_share_mode":
        share_mode(config)
        return utility(config)
    elif select == "tool_phone_prefill":
        save_phone(config)
        return utility(config)
    elif select == "tool_proxy_setting":
        use_proxy(config)
        return utility(config)
    elif select == "tool_capacha_mode":
        captcha_mode(config)
        return utility(config)
    elif select == "tool_pushplus":
        pushplus_config(config)
        return utility(config)
    elif select == "tool_bark":
        bark_config(config)
        return utility(config)
    elif select == "tool_dingding":
        dingding_config(config)
        return utility(config)
    elif select == "tool_wx_push":
        wx_config(config)
        return utility(config)
    elif select == "tool_ftqq":
        ftqq_config(config)
        return utility(config)
    elif select == "tool_smtp":
        smtp_config(config)
        return utility(config)
    elif select =="tool_set_offset":
        set_offset(config)
        return utility(config)
    elif select == "back":
        return
    elif select == "tool_hide_module":
        try:
            name = noneprompt.InputPrompt(
                i18n_format("input_hide_tool"),
                validator=lambda x: x != "" and x.isidentifier(),
            ).prompt(default="")
        except noneprompt.CancelledError:
            logger.info(i18n_format("cancelled"))
            return
        if name == "bw_2024":
            bw_2024(config)
        if name == "super_mode":
            super(config)
        else:
            logger.error(i18n_format("tool_not_supported"))
        return utility(config)
