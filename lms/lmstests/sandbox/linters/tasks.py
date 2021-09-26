import logging

from celery.utils.log import get_task_logger

from lms.lmstests.sandbox.config.celery import app
from lms.lmstests.sandbox.linters import base


_logger: logging.Logger = get_task_logger(__name__)
_logger.setLevel(logging.INFO)


@app.task
def run_linters_in_sandbox(solution_file_id: str, code: str, file_suffix: str):
    _logger.info('Start running sandbox check solution %s', solution_file_id)
    get_linter = base.BaseLinter.get_match_linter

    try:
        checker = get_linter(_logger, code, file_suffix, solution_file_id)
    except NotImplementedError:
        _logger.info('All linters must implement BaseLinter core methods.')
        raise

    if checker is None:
        _logger.info('No suitable linter for file %s', solution_file_id)
        return []

    checker.initialize()
    try:
        return checker.run_check()
    except Exception:  # NOQA: B902
        _logger.exception("Can't check solution %s", solution_file_id)
        return []
