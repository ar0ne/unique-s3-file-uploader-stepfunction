import logging

logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    logger.info("Create new record in DB and check if file hash exists in table")

    # check if file hash exists in Table "Records"
    exists = False
    # create and save new record
    # Record(user_id=..., file=..., folder=..., created_at=now(),)

    return {
        **event,
        "exists": exists
    }

