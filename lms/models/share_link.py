from typing import Tuple

from flask_login import current_user

from lms.lmsdb.models import SharedSolution, Solution
from lms.lmsweb import webapp
from lms.models.errors import fail


def get(solution_id: int) -> Tuple[Solution, SharedSolution]:
    solution = Solution.get_or_none(solution_id)
    if solution is None:
        return fail(404, f'No such solution {solution_id}')

    solver_id = solution.solver.id
    if solver_id != current_user.id and not current_user.role.is_manager:
        return fail(403, "You aren't allowed to access this page.")

    if not webapp.config.get('SHAREABLE_SOLUTIONS', False):
        return fail(404, 'Shareable solutions are not allowed.')

    shared_solution = SharedSolution.get_or_none(
        SharedSolution.solution == solution,
    )
    return solution, shared_solution
