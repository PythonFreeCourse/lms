import logging

from celery.utils.log import get_task_logger

from lms.lmstests.public.config.celery import app
from lms.lmstests.public.identical_tests import services


_logger: logging.Logger = get_task_logger(__name__)
_logger.setLevel(logging.INFO)


@app.task
def solve_solution_with_identical_code(solution_pk: str) -> None:
    try:
        _logger.info(
            'Start solve_solution_with_identical_code solution %s',
            solution_pk,
        )
        checker = services.IdenticalSolutionSolver(solution_pk, _logger)
        checker.initialize()
        checker.check_identical()
    except Exception:
        _logger.exception(
            'Failed check_if_other_solutions_can_be_solved solution %s',
            solution_pk,
        )


@app.task
def check_if_other_solutions_can_be_solved(solution_pk: str) -> None:
    try:
        _logger.info(
            'Start check_if_other_solutions_can_be_solved solution %s',
            solution_pk,
        )
        checker = services.IdenticalSolutionSolver(solution_pk, _logger)
        checker.initialize()
        checker.check_for_match_solutions_to_solve()
    except Exception:
        _logger.exception(
            'Failed check_if_other_solutions_can_be_solved solution %s',
            solution_pk,
        )
