from flask import request
from flask_login import current_user  # type: ignore

from lms.lmsdb.models import SharedSolution, SharedSolutionEntry, Solution
from lms.lmsweb import webapp
from lms.models.errors import ForbiddenPermission, ResourceNotFound


def get_or_create(solution_id: int) -> SharedSolution:
    if not webapp.config.get('SHAREABLE_SOLUTIONS', False):
        raise ForbiddenPermission('Shareable solutions are not allowed.', 403)

    solution = Solution.get_or_none(solution_id)
    if solution is None:
        raise ResourceNotFound(f'No such solution {solution_id}', 404)

    solver_id = solution.solver.id
    if solver_id != current_user.id and not current_user.role.is_manager:
        raise ForbiddenPermission(
            "You aren't allowed to access this page.", 403,
        )

    shared_solution = SharedSolution.get_or_none(
        SharedSolution.solution == solution,
    )

    if shared_solution is None:
        shared_solution = SharedSolution.create_new(solution=solution)

    return shared_solution


def new_visit(shared_solution: SharedSolution) -> None:
    SharedSolutionEntry.create(
        referrer=request.referrer,
        user=current_user.id,
        shared_solution=shared_solution,
    )
