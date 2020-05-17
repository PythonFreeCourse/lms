import logging

from celery.utils.log import get_task_logger

from lms.lmstests.public.config.celery import app
from lms.lmstests.public.unittests import services


_logger: logging.Logger = get_task_logger(__name__)
_logger.setLevel(logging.INFO)


@app.task
def run_tests_for_solution(solution_id: str, executor_name=None):
    try:
        _logger.info('Start run_tests_for_solution %s', solution_id)
        checker = services.UnitTestChecker(
            logger=_logger,
            solution_id=solution_id,
            executor_name=executor_name,
        )
        checker.initialize()
        checker.run_check()
    except Exception:
        _logger.exception('Failed run_tests_for_solution %s', solution_id)
