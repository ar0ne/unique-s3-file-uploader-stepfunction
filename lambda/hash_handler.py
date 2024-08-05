import logging
import boto3
from hashlib import sha256
from typing import Any

logger = logging.getLogger(__name__)


s3 = boto3.client("s3")


def lambda_handler(event, context) -> dict[str, Any]:
    logger.info("Read file from s3 to calculate hash")

    bucket = event["detail"]["bucket"]["name"]
    key = event["detail"]["object"]["key"]

    # we expect that file only could be `folder/filename`
    if "/" in key:
        folder, filename = key.split("/")
    else:
        folder, filename = None, key

    data = s3.get_object(Bucket=bucket, Key=key)
    body = data["Body"].read()


    h = sha256(body)
    digest = h.hexdigest()

    return {
        "key": key,
        "filename": filename,
        "folder": folder,
        "bucket": bucket,
        "hash": digest,
        "algorithm": "SHA256",
    }
