import logging
import os
import pymysql


log = logging.getLogger(__file__)

dirname = os.path.dirname(__file__)



def lambda_handler(event, context) -> None:
    log.info("Init DB lambda handler")

    connection = pymysql.connect(host=os.environ["DB_HOST"],
                             user=os.environ["DB_USER"],
                             password=os.environ["DB_PASSWORD"],
                             database=os.environ["DB_NAME"],
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)

    statements = None
    with open(os.path.join(dirname, "./sql/init_db.sql")) as f:
        statements = f.read().split(";")
    
    with connection:
        with connection.cursor() as cursor:
            for stmt in statements:
                sql = stmt.strip()
                if not sql:
                    continue
                cursor.execute(sql)
        
        connection.commit()

        with connection.cursor() as cursor:
            sql = "SELECT `user_id`, `name`, `created_at` FROM `users`"
            cursor.execute(sql)
            result = cursor.fetchall()
            log.warning(result)
        

    log.info("DB Init completed")
