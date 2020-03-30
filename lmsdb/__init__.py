from . import database_config
from . import models

database = database_config.get_db_instance()

__all__ = [
    'database',
    'models',
]
