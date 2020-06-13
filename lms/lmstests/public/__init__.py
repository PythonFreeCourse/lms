import os

import sentry_sdk
from sentry_sdk.integrations import celery

from lms.lmstests.public.config import celery as celery_config
from lms.lmstests.public.flake8 import tasks as flake8_tasks
from lms.lmstests.public.identical_tests import tasks as identical_tests_tasks
from lms.lmstests.public.unittests import tasks as unittests_tasks
from lms.lmstests.public.general import tasks as general_tasks

celery_app = celery_config.app

sentry_sdk.init(
    dsn=os.getenv('SENTRY_SDK_DSN', 'https://stub@stub/1'),
    integrations=[celery.CeleryIntegration()],
)


__all__ = (
    'flake8_tasks',
    'celery_app',
    'identical_tests_tasks',
    'general_tasks',
    'unittests_tasks',
)
