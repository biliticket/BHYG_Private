# Copyright (c) 2023-2024 ZianTT, FriendshipEnder
import time
import importlib
import requests


from loguru import logger

# REF: https://github.com/mikumifa/biliTickerBuy
# REF: https://github.com/Amorter/biliTicker_gt
# LICENSE: GPL-3.0

from i18n import i18n_format


def run(gt, challenge, token, mode="local_gt", key=None):
    if mode == "local_gt":
        try:
            validator = Validator()
            validate_string = validator.validate(gt, challenge)
            data = {
                "success": True,
                "challenge": challenge,
                "validate": validate_string,
                "seccode": validate_string,
            }

            return data
        except Exception as e:
            print(f"Error: {e}")
    elif mode == "rrocr":
        # http://api.rrocr.com/api/recognize.html
        param = {
            "appkey": key,
            "gt": gt,
            "challenge": challenge,
            "referer": "https://show.bilibili.com",
        }
        try:
            response = requests.post(
                "http://api.rrocr.com/api/recognize.html", data=param
            ).json()
        except Exception as e:
            print(f"Error: {e}")
            return
        if response["status"] == 0:
            data = {
                "success": True,
                "challenge": response["data"]["challenge"],
                "validate": response["data"]["validate"],
                "seccode": response["data"]["validate"],
            }
            return data
        else:
            print(f"Error: {response['msg']}")
    elif mode == "manual":
        logger.info(i18n_format("manual_verify"))
        logger.info(gt + " " + challenge)
        import pyperclip

        try:
            pyperclip.copy(gt + " " + challenge)
        except pyperclip.PyperclipException:
            logger.error(i18n_format("manual_copy"))
        validate = input(i18n_format("input_captcha"))
        data = {
            "success": True,
            "challenge": challenge,
            "validate": validate,
            "seccode": validate,
        }
        return data
    else:
        logger.critical(i18n_format("captcha_mode_not_supported"))


class Validator:
    def __init__(self):
        try:
            logger.info(i18n_format("try_load_local_captcha"))
            bili_ticket_gt_python = importlib.import_module("bili_ticket_gt_python")
            logger.info(i18n_format("load_success"))
        except Exception as e:
            logger.error(i18n_format("local_captcha_load_failed".format(e)))
            raise KeyboardInterrupt
        self.click = bili_ticket_gt_python.ClickPy()
        pass

    def validate(self, gt, challenge) -> str:
        try:
            validate = self.click.simple_match_retry(gt, challenge)
            return validate
        except Exception as e:
            return ""


if __name__ == "__main__":
    import random

    captcha = requests.get(
        "https://www.geetest.com/demo/gt/register-slide-official?t="+str(random.randint(0, 9999)),
        headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/618.1.15.10.15 (KHTML, like Gecko) Mobile/21F90 BiliApp/77900100 os/ios model/iPhone 15 mobi_app/iphone build/77900100 osVer/17.5.1 network/2 channel/AppStore c_locale/zh-Hans_CN s_locale/zh-Hans_CH disable_rcmd/0 "
            + str(random.randint(0, 9999)),
        },
    ).json()
    gt = captcha["gt"]
    challenge = captcha["challenge"]
    token = '1'
    # validate = run(gt, challenge, token)
    start_time = time.time()
    validate = run(gt, challenge, token, mode="local_gt")
    print(f"Time: {time.time() - start_time}")
    print(validate)
