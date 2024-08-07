import logging
import os
import pymysql
import boto3

log = logging.getLogger(__file__)

dirname = os.path.dirname(__file__)

sm_client = boto3.client("secretsmanager")

password = sm_client.get_secret_value(SecretId=os.environ["SECRET"])["SecretString"]

connection = pymysql.connect(
    host=os.environ["DB_HOST"],
    user=os.environ["DB_USER"],
    password=password,
    database=os.environ["DB_NAME"],
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)


SQL_FILE = os.path.join(dirname, "./sql/init_db.sql")


def lambda_handler(event, context) -> None:
    log.info("Init DB lambda handler")

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
