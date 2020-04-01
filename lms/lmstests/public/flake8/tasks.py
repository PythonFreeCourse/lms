import logging

from celery.utils.log import get_task_logger

from lms.lmstests.public.config.celery import app
from lms.lmstests.public.flake8 import services


_logger: logging.Logger = get_task_logger(__name__)
_logger.setLevel(logging.INFO)


@app.task
def run_flake8_on_solution(solution_pk: str) -> None:
    try:
        _logger.info('Start running check solution %s', solution_pk)
        checker = services.PyFlakeChecker(solution_pk, _logger)
        checker.initialize()
        checker.run_check()
    except Exception:
        _logger.exception('Failed to check solution %s', solution_pk)
