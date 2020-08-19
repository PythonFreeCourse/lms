import logging

from celery.utils.log import get_task_logger

from lms.lmstests.sandbox.config.celery import app
from lms.lmstests.sandbox.flake8 import services


_logger: logging.Logger = get_task_logger(__name__)
_logger.setLevel(logging.INFO)


@app.task
def run_flake8_on_sandbox_on_code(solution_file_id: str, code: str):
    try:
        _logger.info(
            'Start running sandbox check solution %s', solution_file_id)
        checker = services.PyFlakeFileScanner(
            logger=_logger,
            code=code,
            solution_file_id=solution_file_id,
        )
        checker.initialize()
        response = checker.run_check()
        return response
    except Exception:
        _logger.exception('Failed to check solution %s', solution_file_id)
