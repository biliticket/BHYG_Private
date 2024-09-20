from main import main
from loguru import logger
from i18n import i18n_format
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
import atexit
import sys
import base64
import json
import qrcode
import requests
import sentry_sdk
import kdl
import ntplib
import machineid
import pyperclip
import jwt
import base64
import platform
import os
import sys
import json
import importlib
import shutil
import noneprompt


def cleanup_meipass() -> None:
    from sentry_sdk import Hub

    client = Hub.current.client
    if client is not None:
        client.close(timeout=2.0)
    logger.info(i18n_format("exit_sleep_15s"))
    try:
        time.sleep(15)
    except KeyboardInterrupt:
        pass
    if hasattr(sys, "_MEIPASS"):
        meipass_path = sys._MEIPASS  # type: ignore
        try:
            shutil.rmtree(meipass_path)
            print(i18n_format("cleaning_files").format(meipass_path))
        except Exception as e:
            print(i18n_format("cleaning_fail").format(meipass_path, e))


atexit.register(cleanup_meipass)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info(i18n_format("exit_manual"))



