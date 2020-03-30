import os

from peewee import (
    PostgresqlDatabase,
    SqliteDatabase,
)

DB_NAME = os.getenv('DB_NAME', 'lms')
DB_USER = os.getenv('DB_USER', 'lms')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_AUTOROLLBACK = os.getenv('DB_AUTOROLLBACK')

if os.getenv('LOCAL_SETUP'):
    database = SqliteDatabase('db.sqlite')
else:
    db_config = {
        'database': DB_NAME,
        'user': DB_USER,
        'port': DB_PORT,
        'host': DB_HOST,
        'password': DB_PASSWORD,
        'autorollback': DB_AUTOROLLBACK,
    }
    database = PostgresqlDatabase(**db_config)


def get_db_instance():
    return database
