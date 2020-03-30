from lmslinter import config
from lmslinter import flake8

celery_app = config.celery_app

__all__ = ('celery_app', 'flake8')
