import logging

logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    logger.info("Hello from record handler")
    return {
        "hash": "abc1234",
        "id": 12,
        "exists": True,
    }

