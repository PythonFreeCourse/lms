from lms.lmstests import config
from lms.lmstests import flake8

celery_app = config.celery_app

__all__ = ('celery_app', 'flake8')
