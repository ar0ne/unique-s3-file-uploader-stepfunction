import logging
import boto3
from hashlib import sha256

logger = logging.getLogger(__name__)


s3 = boto3.client("s3")


def lambda_handler(event, context) -> dict[str, str]:
    logger.info("Read file from s3 to calculate hash")

    bucket = event["detail"]["bucket"]["name"]
    filename = event["detail"]["object"]["key"]

    data = s3.get_object(Bucket=bucket, Key=filename)
    body = data["Body"].read()


    h = sha256(body)

    return {
        "filename": filename,
        "bucket": bucket,
        "hash": h.hexdigest(),
        "algorithm": "SHA256",
    }
