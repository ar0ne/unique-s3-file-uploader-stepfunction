import logging

logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    logger.info("Hello copy file to gallery handler")
    return {
        "hash": "abc1234",
        "copied": True
    }
