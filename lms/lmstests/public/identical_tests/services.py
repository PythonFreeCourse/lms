import collections
import logging

from lms import notifications
from lms.lmsdb import models


class IdenticalSolutionSolver:
    def __init__(
            self,
            solution_check_pk: str,
            logger: logging.Logger,
    ):
        self._solution_id = solution_check_pk
        self._solution = None
        self._logger = logger

    def initialize(self):
        self._solution = models.Solution.get_by_id(self._solution_id)

    @property
    def solution(self) -> models.Solution:
        return self._solution

    def check_identical(self):
        solution = self._get_first_identical_solution()
        if solution is None:
            return

        self._logger.info(
            'solution %s matched to an checked solution %s. '
            'fork the comments and solve',
            self.solution.id, solution.id,
        )
        self._clone_solution_comments(
            from_solution=solution,
            to_solution=self.solution,
        )

    def _get_first_identical_solution(self):
        return models.Solution.select().join(
            models.Exercise,
        ).filter(**{
            models.Solution.exercise.name:
                self.solution.exercise,
            models.Solution.state.name:
                models.Solution.STATES.DONE.name,
            models.Solution.json_data_str.name:
                self.solution.json_data_str,
        }).first()

    def check_for_match_solutions_to_solve(self):
        for solution in models.Solution.select().join(
                models.Exercise,
        ).filter(**{
            models.Solution.exercise.name:
                self.solution.exercise,
            models.Solution.state.name:
                models.Solution.STATES.CREATED.name,
            models.Solution.json_data_str.name:
                self.solution.json_data_str,
        }):
            self._clone_solution_comments(
                from_solution=self.solution,
                to_solution=solution,
            )

    @staticmethod
    def _clone_solution_comments(
            from_solution: models.Solution,
            to_solution: models.Solution,
    ) -> None:
        user_comments = models.Comment.by_solution(
            from_solution.id,
        ).filter(~models.Comment.is_auto)
        for comment in user_comments:
            models.Comment.create_comment(
                commenter=models.User.get_system_user(),
                line_number=comment.line_number,
                comment_text=comment.comment,
                solution=to_solution,
                is_auto=True,
            )

        to_solution.checker = from_solution.checker
        to_solution.state = from_solution.state
        to_solution.save()
        notifications.create_notification(
            notification_type=(notifications.SolutionCheckedNotification
                               .notification_type()),
            for_user=to_solution.solver,
            solution=to_solution,
        )

    @staticmethod
    def check_identical_solutions_per_exercise():
        same = collections.Counter()
        for exercise in models.Exercise.select():
            solutions = models.Solution.select().join(models.Exercise).filter(
                models.Solution.exercise == exercise)
            for solution in solutions:
                solution_key = f'{exercise.subject}-{solution.json_data_str}'
                if solution_key in same:
                    continue
                count = models.Comment.select().join(models.Solution).filter(
                    models.Solution.json_data_str == solution.json_data_str,
                    models.Solution.exercise == exercise,
                    models.Solution.solver != solution.solver,
                ).count()
                same[solution_key] = count
        return same
