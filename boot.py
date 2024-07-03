from main import main
from loguru import logger
from i18n import i18n_format

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
