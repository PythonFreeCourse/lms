from lms.lmstests.public.flake8 import tasks as flake8_tasks
from lms.lmstests.public.config import celery as celery_config

celery_app = celery_config.public_app

__all__ = ('flake8_tasks', 'celery_app')
