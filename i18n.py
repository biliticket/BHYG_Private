import noneprompt
from pathlib import Path
import sys
import json
from typing import Any, cast  # type: ignore[reportAny]
from loguru import logger

# Copyright (c) 2023-2024 ZianTT, FriendshipEnder
i18n_lang = "NaN"
i18n: dict[str, str | list[str]] = {}

LANGUAGE_FILE = Path.cwd() / "language"
PROGRAM_BASEDIR = Path(sys._MEIPASS) if getattr(sys, "frozen", None) else Path.cwd()  # type: ignore[all]
LANGUAGE_PATH = PROGRAM_BASEDIR / "langs"


class LamguageLoadError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


def set_language(force_reload: bool):
    global i18n, i18n_lang
    if not force_reload and LANGUAGE_FILE.exists():  # 加载语言文件
        i18n_lang = LANGUAGE_FILE.read_text(encoding="utf-8")
        logger.info(f"Try loading lauguage: {i18n_lang}")
        try:
            i18n = json.loads(
                (LANGUAGE_PATH / f"{i18n_lang}.json").read_text(encoding="utf-8")
            )["data"]
        except FileNotFoundError as e:
            LANGUAGE_FILE.unlink(missing_ok=True)
            raise LamguageLoadError(
                "Language loading failed, please restart the program."
            ) from e
    else:  # 加载语言文件不存在时, 创建一个语言文件
        language_list = [
            (cast(str, j["id"]), cast(str, j["name"]))
            for j in (
                cast(dict[str, Any], json.loads(i.read_text(encoding="utf-8")))
                for i in LANGUAGE_PATH.glob("*.json")
            )
        ]
        try:
            i18n_lang = (
                noneprompt.ListPrompt(
                    question="请选择一个语言 / Please select a language",
                    choices=[
                        noneprompt.Choice(name=f"{name} ({id})", data=id)
                        for id, name in language_list
                    ],
                )
                .prompt()
                .data
            )
        except noneprompt.CancelledError as e:
            logger.info("Cancelled by user.")
            raise KeyboardInterrupt("Cancelled by user") from e
        _ = LANGUAGE_FILE.write_text(i18n_lang, encoding="utf-8")
        i18n = json.loads(
            (LANGUAGE_PATH / f"{i18n_lang}.json").read_text(encoding="utf-8")
        )["data"]


def i18n_format(key: str) -> str:
    global i18n
    try:
        return "\n".join(i18n[key]) if isinstance(i18n[key], list) else str(i18n[key])
    except KeyError:
        try:
            temp_lang: dict[str, str] = json.loads(
                (LANGUAGE_PATH / "zh_cn.json").read_text(encoding="utf-8")
            )["data"]
            return (
                "\n".join(temp_lang[key])
                if isinstance(temp_lang[key], list)
                else str(temp_lang[key])
            )
        except KeyError:
            return key
