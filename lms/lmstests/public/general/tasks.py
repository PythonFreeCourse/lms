import logging

from celery.utils.log import get_task_logger

from lms.lmsdb import models
from lms.lmstests.public.config.celery import app


_logger: logging.Logger = get_task_logger(__name__)
_logger.setLevel(logging.INFO)


@app.task
def reset_solution_state_if_needed(solution_pk: str) -> None:
    _logger.info('reset_solution_state_if_needed: solution %s', solution_pk)

    try:
        solution = models.Solution.get_by_id(solution_pk)
    except models.Solution.DoesNotExist:
        _logger.exception('Solution %s does not exist', solution_pk)
        raise

    if solution.state == models.Solution.STATES.IN_CHECKING.name:
        _logger.info('Reset solution %s to CREATED state', solution_pk)
        solution.set_state(models.Solution.STATES.CREATED)
