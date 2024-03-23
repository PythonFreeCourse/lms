from collections.abc import Iterable
import tempfile
from typing import cast

from flake8.main import application

from lms.lmstests.sandbox.linters import defines
from lms.lmstests.sandbox.linters.base import BaseLinter, LinterError


class PythonLinter(BaseLinter):
    def initialize(self):
        self._app = application.Application()
        self._argv = ['--import-order-style', 'google']

    @property
    def app(self) -> application.Application:
        return self._app

    def get_error_text(self, error: LinterError) -> str:
        default_text = f'{error.error_code}-{error.text}'
        return defines.FLAKE_ERRORS_MAPPING.get(error.error_code, default_text)

    @staticmethod
    def match_to_file_suffix(file_suffix: str) -> bool:
        return file_suffix.lower() == 'py'

    def _get_errors_from_solution(self) -> Iterable[LinterError]:
        with tempfile.NamedTemporaryFile('w') as temp_file:
            temp_file.write(self._code)
            temp_file.flush()
            self.app.initialize(argv=[temp_file.name, *self._argv])
            self.app.run_checks()
            assert self.app.file_checker_manager is not None
            artifacts = self.app.file_checker_manager.results
            results = [r for _, results_, _ in artifacts for r in results_]

        for result in results:
            assert isinstance(result, tuple)
            result = cast(tuple, result)
            response = LinterError(
                *result, solution_file_id=self._solution_file_id,
            )
            if response.error_code in defines.FLAKE_SKIP_ERRORS:
                self._logger.info(
                    'Skipping error %s on line %s to solution file %s',
                    response.error_code,
                    response.line_number,
                    self._solution_file_id,
                )
            else:
                yield response
