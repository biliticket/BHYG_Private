

import json
import time

import requests


from loguru import logger
import bili_ticket_gt_python


class Validator():
    import bili_ticket_gt_python
    def __init__(self):
        import bili_ticket_gt_python
        self.click = bili_ticket_gt_python.ClickPy()
        pass

    def validate(self, gt, challenge) -> str:
        try:
            validate = self.click.simple_match_retry(gt, challenge)
            return validate
        except Exception as e:
            return ""


def local_geetest(gt, challenge, token):

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
