from lms.lmstests.sandbox.flake8 import tasks as flake8_tasks
from lms.lmstests.sandbox.config import celery as celery_config

celery_app = celery_config.app

__all__ = ('flake8_tasks', 'celery_app')
