import logging

from celery.utils.log import get_task_logger

from lms.lmsdb import models
from lms.lmstests.public.config.celery import app
from lms.lmstests.public.unittests import services


_logger: logging.Logger = get_task_logger(__name__)
_logger.setLevel(logging.INFO)


@app.task
def run_tests_for_solution(solution_id: str, executor_name=None):
    _logger.info('Start run_tests_for_solution %s', solution_id)
    checker = services.UnitTestChecker(_logger, solution_id, executor_name)
    try:
        checker.initialize()
    except models.Solution.DoesNotExist:
        _logger.exception('The solution %s does not exists', solution_id)
        raise
    except models.ExerciseTest.DoesNotExist:
        _logger.exception('Missing tests for solution %s', solution_id)
        raise

    checker.run_check()
