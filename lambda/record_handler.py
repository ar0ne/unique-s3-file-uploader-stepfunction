import logging
import pymysql

logger = logging.getLogger(__name__)


USER_ID = 10001

FIND_RECORD_WITH_HASH = "SELECT EXISTS(SELECT * FROM `files` WHERE `hash` =%s LIMIT 1"


def lambda_handler(event, context):
    logger.info("Create new record in DB and check if file hash exists in table")

    connection = pymysql.connect(host=os.environ["DB_HOST"],
                                user=os.environ["DB_USER"],
                                password=os.environ["DB_PASSWORD"],
                                database=os.environ["DB_NAME"],
                                charset='utf8mb4',
                                cursorclass=pymysql.cursors.DictCursor)

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(FIND_RECORD_WITH_HASH, (event["hash"],))
            result = cursor.fetchone()
            logger.warning(f"{result=}")
        connection.commit()


    # check if file hash exists in Table "Records"
    exists = False
    # create and save new record
    # Record(user_id=..., file=..., folder=..., created_at=now(),)

    return {
        **event,
        "exists": exists
    }

