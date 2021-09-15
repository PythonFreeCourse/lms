import logging

from celery.utils.log import get_task_logger

from lms.lmstests.sandbox.config.celery import app
from lms.lmstests.sandbox.linters import base


_logger: logging.Logger = get_task_logger(__name__)
_logger.setLevel(logging.INFO)


@app.task
def run_linters_in_sandbox(solution_file_id: str, code: str, file_suffix: str):
    _logger.info('Start running sandbox check solution %s', solution_file_id)

    try:
        checker = base.BaseLinter.get_match_linter(
            logger=_logger,
            code=code,
            file_suffix=file_suffix,
            solution_file_id=solution_file_id,
        )
    except NotImplemented:
        _logger.info(f'No suitable linter for file {solution_file_id}')
        return []

    checker.initialize()
    try:
        return checker.run_check()
    except Exception:  # NOQA: B902
        _logger.exception(f"Can't check {solution_file_id}")
