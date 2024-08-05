import logging

logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    logger.info("Delete file from S3 user bucket")
    return {
        "hash": "abc1234",
        "deleted": True
    }
