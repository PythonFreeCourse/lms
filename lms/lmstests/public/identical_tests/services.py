import collections
import logging

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
        for solution in models.Solution.select().join(
                models.Exercise,
        ).filter(**{
            models.Solution.exercise.name: self.solution.exercise,
            models.Solution.is_checked.name: True,
            models.Solution.json_data_str.name: self.solution.json_data_str,
        }):
            self._logger.info(
                'solution %s matched to an checked solution %s. '
                'fork the comments and solve',
                self.solution.id, solution.id,
            )
            self._clone_solution_comments(
                from_solution=solution,
                to_solution=self.solution,
            )
            break

    def check_if_can_solve_other_solutions(self):
        for solution in models.Solution.select().join(
                models.Exercise,
        ).filter(**{
            models.Solution.exercise.name: self.solution.exercise,
            models.Solution.is_checked.name: False,
            models.Solution.json_data_str.name: self.solution.json_data_str,
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
        for comment in models.Comment.by_solution(
                from_solution.id,
        ).filter(**{
            '__'.join((
                models.Comment.comment.name,
                models.CommentText.flake8_key.name,
            )): None,
        }):
            models.Comment.create_comment(
                commenter=models.User.get_system_user(),
                line_number=comment.line_number,
                comment_text=comment.comment,
                solution=to_solution,
            )

        to_solution.checker = from_solution.checker
        to_solution.is_checked = from_solution.is_checked
        to_solution.save()

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
