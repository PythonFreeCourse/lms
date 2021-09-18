import logging

from celery.exceptions import OperationalError, TaskError
from celery.utils.log import get_task_logger

from lms.lmsdb import models
from lms.lmstests.public.config.celery import app
from lms.lmstests.public.linters import services


_logger: logging.Logger = get_task_logger(__name__)
_logger.setLevel(logging.INFO)


@app.task
def run_linter_on_solution(solution_pk: str) -> None:
    _logger.info('Start running check solution %s', solution_pk)
    checker = services.LinterChecker(solution_pk, _logger)

    try:
        checker.initialize()
    except models.Solution.DoesNotExist:
        _logger.exception('Solution %s does not exist', solution_pk)
        raise

    try:
        checker.run_check()
    except (TaskError, OperationalError):
        _logger.exception('Failed to check solution %s', solution_pk)
