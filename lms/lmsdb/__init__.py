from lms.lmsdb import database_config
from lms.lmsdb import models

database = database_config.get_db_instance()

__all__ = [
    'database',
    'models',
]
