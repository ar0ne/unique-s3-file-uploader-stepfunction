import logging
import os


log = logging.getLogger(__file__)

def lambda_handler(event, context):
    log.info("Init DB lambda handler")

    log.warning(f"ENV: {os.environ}")
