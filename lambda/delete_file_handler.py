import logging
import boto3

logger = logging.getLogger(__name__)

s3 = boto3.client("s3")


def lambda_handler(event, context) -> dict[str, str]:
    logger.info("Delete file from user's S3 bucket")

    s3.delete_object(Bucket=event['bucket'], Key=event['key'])

    return {
        **event,
        "deleted": True
    }
