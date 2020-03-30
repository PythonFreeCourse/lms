from . import database_config

database = database_config.get_db_instance()

__all__ = [
    'database',
]
