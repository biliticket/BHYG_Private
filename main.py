# -*- coding: UTF-8 -*-
# Copyright (c) 2023-2024 ZianTT, FriendshipEnder
import json
import os
import threading
import time


import noneprompt

import requests
from loguru import logger

from api import BilibiliHyg
from push import PUSH
from globals import *

from utils import save, load, check_policy

import noneprompt

from i18n import *

def run(hyg): # 核心抢票逻辑
    if "super" in hyg.config:
        logger.info(i18n_format("super_mode_on_msg"))
    match hyg.config["mode"]:
        case "direct" | "time":
            while True:
                if hyg.try_create_order():
                    hyg.sdk.capture_message("Pay success!")
                    logger.success(i18n_format("pay_success"))
                    PUSH.push(hyg.push_self,i18n_format("pay_success"))
                    return
        case "detect":
            token_time = time.time()
            while 1:
                if time.time() - token_time > 300:
                    token_time = time.time()
                    try:
                        hyg.get_token()
                    except:
                        continue
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
                            hyg.sdk.capture_message("Pay success!")
                            logger.success(i18n_format("pay_success"))
                            return
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


def main(): # 主程序启动逻辑
    from globals import version, version_beta_msg, version_beta
    if version_beta:
        logger.warning(version_beta_msg)

    set_language(False)
    print(i18n_format("start_up").format(version))
    try:
        sentry_sdk = init(version)
        session = requests.session()

        check_key = check_policy()
        logger.info(i18n_format("tips"))
        config = load_config()
        push_self= PUSH(config)
        if config == None:
            return
        if check_key:
            check_policy(uid=config["uid"])
        if "super" in config:
            check_policy(uid=config["uid"], res="super")

        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 15;; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/132.0.6834.163 Mobile Safari/537.36 os/android model/BHYG66 build/8300300 osVer/15 sdkInt/35 network/1 BiliApp/8300300 mobi_app/android channel/master Buvid/XUB12BCB16D20812E103A164ED829711BA789 sessionID/27d578d0 innerVer/8300310 c_locale/zh_CN s_locale/zh_CN disable_rcmd/0 themeId/2 sh/40",
            "Cookie": config["cookie"],
        }
        if "user-agent" in config:
            headers["User-Agent"] = config["user-agent"]
        session = requests.Session()
        
        BHYG = BilibiliHyg(config, sentry_sdk)
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
    logger.info(i18n_format("exit_sleep_15s"))
    try:
        time.sleep(15)
    except KeyboardInterrupt:
        pass
