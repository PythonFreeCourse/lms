from lmsdb import database_config
from lmsdb import models

database = database_config.get_db_instance()

__all__ = [
    'database',
    'models',
]
