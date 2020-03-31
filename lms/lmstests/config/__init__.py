from lms.lmstests.config import celery

celery_app = celery.app

__all__ = ('celery_app',)
