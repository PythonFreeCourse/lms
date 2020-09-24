import collections
import logging
import typing

from flask_babel import gettext as _

from lms.lmsdb import models
from lms.models import notifications
from lms.lmsweb import routes


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
        solution_file = self._get_first_identical_solution_file()
        if solution_file is None:
            return

        solution = solution_file.solution
        if solution.solution_files.count() != 1:
            self._logger.info(
                'Skip multiple files identical check on solution %s',
                solution,
            )

        self._logger.info(
            'solution %s matched to an checked solution %s. '
            'fork the comments and solve',
            self.solution.id, solution.id,
        )
        self._clone_solution_comments(
            from_solution=solution,
            to_solution=self.solution,
        )

    def _get_first_identical_solution_file(
            self,
    ) -> typing.Optional[models.SolutionFile]:
        match_code = self.solution.solution_files.get().code
        return models.SolutionFile.select().join(
            models.Solution,
        ).filter(
            models.Solution.exercise == self.solution.exercise,
            models.Solution.state == models.Solution.STATES.DONE.name,
            models.SolutionFile.code == match_code,
        ).first()

    def check_for_match_solutions_to_solve(self):
        if self.solution.solution_files.count() != 1:
            return

        match_code = self.solution.solution_files.get().code
        for solution_file in models.SolutionFile.select().join(
                models.Solution,
        ).filter(
            models.Solution.exercise == self.solution.exercise,
            models.Solution.state == models.Solution.STATES.CREATED.name,
            models.SolutionFile.code == match_code,
        ):
            self._clone_solution_comments(
                from_solution=self.solution,
                to_solution=solution_file.solution,
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
                file=to_solution.solution_files.get(),
                is_auto=True,
            )

        to_solution.checker = from_solution.checker
        to_solution.state = from_solution.state
        to_solution.save()
        notifications.send(
            kind=notifications.NotificationKind.CHECKED,
            user=to_solution.solver,
            related_id=to_solution,
            message=_(
                'הפתרון שלך לתרגיל %(subject)s נבדק.',
                subject=to_solution.exercise.subject,
            ),
            action_url=f'{routes.SOLUTIONS}/{to_solution.id}',
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
