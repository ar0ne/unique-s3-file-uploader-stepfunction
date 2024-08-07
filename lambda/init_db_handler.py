import logging
import os
import pymysql
import json
from utils import get_secret


log = logging.getLogger(__file__)

dirname = os.path.dirname(__file__)


secret = json.loads(get_secret(os.environ["SECRET"]))
password = secret["password"]

SQL_FILE = os.path.join(dirname, "./sql/init_db.sql")


def lambda_handler(event, context) -> None:
    log.info("Init DB lambda handler")

    connection = pymysql.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=password,
        database=os.environ["DB_NAME"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )

    statements = None
    with open(SQL_FILE) as f:
        statements = f.read().split(";")

    with connection:
        with connection.cursor() as cursor:
            for stmt in statements:
                sql = stmt.strip()
                if not sql:
                    continue
                cursor.execute(sql)

        connection.commit()

    log.info("DB Init completed")
