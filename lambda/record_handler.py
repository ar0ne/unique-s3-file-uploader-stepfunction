import os
import logging
import pymysql

logger = logging.getLogger(__name__)


FIND_RECORD_WITH_HASH = "SELECT file_id FROM `files` WHERE `hash` =%s LIMIT 1;"
CREATE_NEW_RECORD = "INSERT INTO `records` (user_id, file_id, filename, folder) VALUES (%s, %s, %s, %s);"
CREATE_NEW_FILE = "INSERT INTO `files` (hash, algorithm) VALUES (%s, %s);"


def lambda_handler(event, context):
    logger.info("Create new record in DB and check if file hash exists in table")

    connection = pymysql.connect(host=os.environ["DB_HOST"],
                                user=os.environ["DB_USER"],
                                password=os.environ["DB_PASSWORD"],
                                database=os.environ["DB_NAME"],
                                charset='utf8mb4',
                                cursorclass=pymysql.cursors.DictCursor)

    file_id = None
    file_exists = False
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(FIND_RECORD_WITH_HASH, (event["hash"],))
            result = cursor.fetchone()
            file_exists = bool(result)
            file_id = result["file_id"] if file_exists else None
            
            # create new file
            if not file_id:
                cursor.execute(CREATE_NEW_FILE, (event["hash"], event["algorithm"]))
                cursor.execute("SELECT LAST_INSERT_ID() as ID;")
                result = cursor.fetchone()
                file_id = result["ID"]
                
            # create new record
            cursor.execute(CREATE_NEW_RECORD, (event["user_id"], file_id, event["filename"], event["folder"]))
            cursor.execute("SELECT LAST_INSERT_ID() as ID;")
            result = cursor.fetchone()
            record_id = result["ID"]

        connection.commit()

    return {
        **event,
        "exists": file_exists,
        "file_id": file_id,
        "record_id": record_id,
    }
    

