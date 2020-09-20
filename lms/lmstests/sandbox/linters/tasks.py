import logging

from celery.utils.log import get_task_logger

from lms.lmstests.sandbox.config.celery import app
from lms.lmstests.sandbox.linters import base


_logger: logging.Logger = get_task_logger(__name__)
_logger.setLevel(logging.INFO)


@app.task
def run_linters_in_sandbox(solution_file_id: str, code: str, file_suffix: str):
    try:
        _logger.info(
            'Start running sandbox check solution %s', solution_file_id)
        checker = base.BaseLinter.get_match_linter(
            logger=_logger,
            code=code,
            file_suffix=file_suffix,
            solution_file_id=solution_file_id,
        )
        if checker is None:
            return []
        else:
            checker.initialize()
            return checker.run_check()
    except Exception:
        _logger.exception('Failed to check solution file %s', solution_file_id)
