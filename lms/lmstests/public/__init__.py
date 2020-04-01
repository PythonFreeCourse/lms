from lms.lmstests.public.config import celery as celery_config
from lms.lmstests.public.flake8 import tasks as flake8_tasks

celery_app = celery_config.app

__all__ = ('flake8_tasks', 'celery_app')
