import os

from lms.lmstests.public.config import celery as celery_config
from lms.lmstests.public.flake8 import tasks as flake8_tasks
from lms.lmstests.public.identical_tests import tasks as identical_tests_tasks
from lms.lmstests.public.unittests import tasks as unittests_tasks
from lms.lmstests.public.general import tasks as general_tasks
from lms.lmstests.sandbox.config import celery_app as sandbox_app

celery_app = celery_config.app

if os.getenv('LOCAL_SETUP'):
    celery_app.conf.update(task_always_eager=True)
    sandbox_app.conf.update(task_always_eager=True)


__all__ = (
    'flake8_tasks',
    'celery_app',
    'identical_tests_tasks',
    'general_tasks',
    'unittests_tasks',
)
