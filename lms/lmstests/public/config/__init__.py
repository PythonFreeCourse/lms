from lms.lmstests.public.config import celery

celery_app = celery.public_app

__all__ = ('celery_app',)
