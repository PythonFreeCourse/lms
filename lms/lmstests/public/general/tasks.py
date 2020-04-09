import logging

from celery.utils.log import get_task_logger

from lms.lmsdb import models
from lms.lmstests.public.config.celery import app


_logger: logging.Logger = get_task_logger(__name__)
_logger.setLevel(logging.INFO)


@app.task
def reset_solution_state_if_needed(solution_pk: str) -> None:
    try:
        _logger.info(
            'Start reset_solution_state_if_needed solution %s',
            solution_pk,
        )
        solution = models.Solution.get_by_id(solution_pk)
        if solution.state == models.Solution.STATES.IN_CHECKING.name:
            _logger.info('Reset solution %s to CREATED state', solution_pk)
            solution.set_state(models.Solution.STATES.CREATED)
    except Exception:
        _logger.exception(
            'Failed reset_solution_state_if_needed solution %s',
            solution_pk,
        )
