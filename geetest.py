# Copyright (c) 2023-2024 ZianTT, FriendshipEnder
import json
import time

import requests


from loguru import logger

from globals import *

# REF: https://github.com/mikumifa/biliTickerBuy
# REF: https://github.com/Amorter/biliTicker_gt
# LICENSE: GPL-3.0



def run(gt, challenge, token, mode="local_gt", key=None):
    if mode == "local_gt":
        import local_geetest
        data=local_geetest.local_geetest(gt, challenge, token)
        return data
    elif mode == "rrocr":
        # http://api.rrocr.com/api/recognize.html
        param = {
            "appkey": "e1db1bc497a8471c9479f600527ef56f",
            "gt": gt,
            "challenge": challenge,
            "referer": "https://show.bilibili.com",
        }
        try:
            response = requests.post("http://api.rrocr.com/api/recognize.html", data=param).json()
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
        print("请手动完成验证码")
        print(gt + " " + challenge)
        import pyperclip
        try:
            pyperclip.copy(gt + " " + challenge)
        except pyperclip.PyperclipException:
            print("请手动复制。若您为linux，请运行`sudo apt-get install xclip`")
        validate = input("请输入验证码：")
        data = {
            "success": True,
            "challenge": challenge,
            "validate": validate,
            "seccode": validate,
        }
        return data
    else:

        logger.critical("暂不支持该验证码模式")
        




if __name__ == "__main__":
    import random
    captcha = requests.get(
        "https://passport.bilibili.com/x/passport-login/captcha", headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/618.1.15.10.15 (KHTML, like Gecko) Mobile/21F90 BiliApp/77900100 os/ios model/iPhone 15 mobi_app/iphone build/77900100 osVer/17.5.1 network/2 channel/AppStore c_locale/zh-Hans_CN s_locale/zh-Hans_CH disable_rcmd/0 "+str(random.randint(0, 9999)),
        }
    ).json()
    gt = captcha["data"]["geetest"]["gt"]
    challenge = captcha["data"]["geetest"]["challenge"]
    token = captcha["data"]["token"]
    # validate = run(gt, challenge, token)
    start_time = time.time()
    validate = run(gt, challenge, token, mode="local_gt")
    print(f"Time: {time.time() - start_time}")
    print(validate)
