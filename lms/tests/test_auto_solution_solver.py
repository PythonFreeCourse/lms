import typing

from lms.lmsdb import models
from lms.lmstests.public.identical_tests import tasks
from lms.models import notifications
from lms.tests import conftest


SOME_CODE = "print('Hello Word')"


class TestAutoSolutionSolver:
    def test_solve_solution_with_identical_code(self, comment: models.Comment):
        f_solution, s_solution = self._duplicate_solution_from_comment(
            comment=comment,
            first_solution_code=SOME_CODE,
            second_solution_code=SOME_CODE,
        )
        assert len(tuple(s_solution.comments)) == 0
        tasks.solve_solution_with_identical_code(s_solution.id)
        assert len(tuple(s_solution.comments)) == 1

        user_notifications = notifications.get(user=s_solution.solver)
        assert len(user_notifications) == 1
        solution_id = user_notifications[0].related_id
        assert s_solution.id == solution_id

        user_notifications = notifications.get(user=f_solution.solver)
        assert len(user_notifications) == 0

    def test_solve_solution_with_identical_code_not_identical_code(
            self,
            comment: models.Comment,
    ):
        _, another_solution = self._duplicate_solution_from_comment(
            comment=comment,
            first_solution_code=SOME_CODE * 2,
            second_solution_code=SOME_CODE,
        )

        assert len(tuple(another_solution.comments)) == 0
        tasks.solve_solution_with_identical_code(another_solution.id)
        assert len(tuple(another_solution.comments)) == 0
        assert another_solution.state == models.Solution.STATES.CREATED.name

    def test_check_if_other_solutions_can_be_solved(
            self,
            comment: models.Comment,
    ):
        first_solution, another_solution = (
            self._duplicate_solution_from_comment(
                comment=comment,
                first_solution_code=SOME_CODE,
                second_solution_code=SOME_CODE,
            ))

        assert len(tuple(another_solution.comments)) == 0
        tasks.check_if_other_solutions_can_be_solved(first_solution.id)
        assert len(tuple(another_solution.comments)) == 1

        user_notifications = notifications.get(user=another_solution.solver)
        assert len(user_notifications) == 1

        subject = user_notifications[0].message
        assert another_solution.exercise.subject in subject

    def test_check_if_other_solutions_can_be_solved_not_identical_code(
            self,
            comment: models.Comment,
    ):
        first_solution, another_solution = (
            self._duplicate_solution_from_comment(
                comment=comment,
                first_solution_code=SOME_CODE,
                second_solution_code=SOME_CODE * 2,
            ))

        assert len(tuple(another_solution.comments)) == 0
        tasks.check_if_other_solutions_can_be_solved(first_solution.id)
        assert len(tuple(another_solution.comments)) == 0

    @staticmethod
    def _duplicate_solution_from_comment(
            comment: models.Comment,
            first_solution_code: str,
            second_solution_code: str,
    ) -> typing.Tuple[models.Solution, models.Solution]:
        first_solution: models.Solution = comment.file.solution
        first_solution.set_state(models.Solution.STATES.DONE)
        first_solution = first_solution.refresh()
        solution_file = first_solution.solution_files.get()
        solution_file.code = first_solution_code
        solution_file.save()
        student_user: models.User = conftest.create_student_user(index=1)
        second_solution = conftest.create_solution(
            exercise=first_solution.exercise,
            student_user=student_user,
            code=second_solution_code,
        )
        return first_solution, second_solution
