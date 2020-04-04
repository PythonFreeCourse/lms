from lms.lmstests.public.config import celery as celery_config
from lms.lmstests.public.flake8 import tasks as flake8_tasks
from lms.lmstests.public.identical_tests import tasks as identical_tests_tasks

celery_app = celery_config.app

__all__ = (
    'flake8_tasks',
    'celery_app',
    'identical_tests_tasks',
)
