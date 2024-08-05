import os
import boto3
import logging
from typing import Any

logger = logging.getLogger(__name__)


s3 = boto3.resource("s3")

def lambda_handler(event, context) -> dict[str, Any]:
    logger.info("Copy file to another bucket")

    copy_to_bucket = os.environ["COPY_TO_BUCKET"] 

    copy_source = {
        'Bucket': event['bucket'],
        'Key': event['filename'],
    }

    bucket = s3.Bucket(copy_to_bucket)
    bucket.copy(copy_source, event['hash'])

    return {
        **event,
        "copied": True
    }
