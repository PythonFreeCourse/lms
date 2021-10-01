import logging
import typing

from celery.result import allow_join_result
from flask_babel import gettext as _  # type: ignore

from lms.lmsdb import models
from lms.lmstests.sandbox import linters
from lms.lmsweb import routes
from lms.models import notifications


LinterError = linters.base.LinterError


class LinterChecker:
    sandbox_tasks = linters.tasks

    def __init__(self, solution_check_pk: str, logger: logging.Logger):
        self._solution_id = solution_check_pk
        self._app = None
        self._solution = None
        self._logger = logger
        self._errors: typing.List[LinterError] = []

    def initialize(self):
        self._solution = models.Solution.get_by_id(self._solution_id)

    @property
    def solution(self) -> models.Solution:
        return self._solution

    def run_check(self):
        self._run_in_sandbox_and_populate_errors()
        self._populate_comments()
        self._fire_notification_if_needed()

    def _run_in_sandbox_and_populate_errors(self):
        self._logger.info(
            'Start running in remote sandbox linters checks on solution %s',
            self._solution_id,
        )
        response = self._run_in_sandbox()
        self._logger.info(
            'End running in remote sandbox linters checks on solution %s',
            self._solution_id,
        )
        for error in response:
            self._errors.append(LinterError(*error))

    def _run_in_sandbox(self):
        results = [
            self.sandbox_tasks.run_linters_in_sandbox.apply_async(
                args=(
                    solution_file.id,
                    solution_file.code,
                    solution_file.suffix,
                ),
            )
            for solution_file in self.solution.solution_files
        ]
        responses = []
        with allow_join_result():
            for result in results:
                responses.extend(result.get())
        return responses

    def _populate_comments(self):
        self._logger.info(
            'populate comments to solution %s',
            self._solution_id,
        )

        for error in self._errors:
            self._logger.info('Adding error %s to solution %s',
                              error, self._solution_id)
            comment_text = models.CommentText.create_comment(
                text=error.text,
                flake_key=error.error_code,
            )
            models.Comment.create_comment(
                commenter=models.User.get_system_user(),
                line_number=error.line_number,
                comment_text=comment_text,
                file=models.SolutionFile.get_by_id(error.solution_file_id),
                is_auto=True,
            )

    def _fire_notification_if_needed(self):
        if not self._errors:
            return

        errors_len = len(self._errors)
        exercise_name = self.solution.exercise.subject
        msg = _(
            'The automatic checker gave you %(errors_num)d for your '
            '%(name)s solution.',
            errors_num=errors_len, name=exercise_name,
        )
        return notifications.send(
            kind=notifications.NotificationKind.FLAKE8_ERROR,
            user=self.solution.solver,
            related_id=self.solution,
            message=msg,
            action_url=f'{routes.SOLUTIONS}/{self.solution.id}',
        )
