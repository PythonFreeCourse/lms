import typing

from sqlfluff.config import FluffConfig
from sqlfluff.errors import SQLBaseError
from sqlfluff.linter import Linter

from lms.lmstests.sandbox.linters import defines
from lms.lmstests.sandbox.linters.base import BaseLinter, LinterError

SQLErrors = typing.Sequence[SQLBaseError]


class SQLLinter(BaseLinter):
    def initialize(self):
        self._app = Linter(config=FluffConfig.from_root())

    @property
    def app(self) -> Linter:
        return self._app

    def get_error_text(self, error: LinterError) -> str:
        return defines.SQL_ERRORS_MAPPING.get(error.text, error.text)

    @staticmethod
    def match_to_file_suffix(file_suffix: str) -> bool:
        return file_suffix.lower() == 'sql'

    def _get_errors_from_solution(self) -> typing.Iterable[LinterError]:
        lint_errors: SQLErrors = self.app.lint_string(self._code).violations
        for result in lint_errors:
            response = LinterError(
                error_code=result.rule_code(),
                line_number=result.line_no(),
                column=result.line_pos(),
                text=result.desc(),
                physical_line='',
                solution_file_id=self._solution_file_id,
            )
            if response.text in defines.SQL_SKIP_ERROR_MESSAGES:
                self._logger.info(
                    'Skipping error %s on line %s to solution file %s',
                    response.error_code,
                    response.line_number,
                    self._solution_file_id,
                )
            else:
                yield response
