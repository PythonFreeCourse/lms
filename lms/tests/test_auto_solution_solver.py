from lms.lmsdb import models
from lms.lmstests.public.identical_tests import tasks
from lms.tests import conftest

SOME_CODE = "print('Hello Word')"


class TestAutoSolutionSolver:
    def test_solve_solution_with_identical_code(self, comment: models.Comment):
        first_solution: models.Solution = comment.solution
        student_user: models.User = conftest.create_student_user(index=1)
        another_solution, _ = models.Solution.create_solution(
            exercise=first_solution.exercise,
            solver=student_user,
        )
        assert len(tuple(another_solution.comments)) == 0
        tasks.solve_solution_with_identical_code(another_solution.id)
        assert len(tuple(another_solution.comments)) == 1
