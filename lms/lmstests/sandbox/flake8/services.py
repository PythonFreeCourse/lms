import logging
import tempfile
import typing

from flake8.main import application

from lms.lmstests.sandbox.flake8 import defines


class PyFlakeResponse(typing.NamedTuple):
    error_code: str
    line_number: int
    column: int
    text: str
    physical_line: str
    solution_file_id: str


class PyFlakeFileScanner:
    def __init__(
            self,
            logger: logging.Logger,
            code: str,
            solution_file_id: str,
    ):
        self._app = None
        self._code = code
        self._logger = logger
        self._solution_file_id = solution_file_id

    def initialize(self):
        self._app = application.Application()
        self._app.initialize(argv=['--import-order-style', 'google'])

    @property
    def app(self) -> application.Application:
        return self._app

    def run_check(self) -> typing.Sequence[PyFlakeResponse]:
        self._logger.info(
            'checks errors on solution file %s', self._solution_file_id)
        errors = self._get_errors_from_solution()
        response = []
        for error in errors:
            if error.error_code in defines.FLAKE_SKIP_ERRORS:
                self._logger.info(
                    'Skipping error %s on line %s to solution file %s',
                    error.error_code,
                    error.line_number,
                    self._solution_file_id,
                )
                continue

            self._logger.info(
                'Adding error %s on line %s to solution file %s',
                error.error_code,
                error.line_number,
                self._solution_file_id,
            )
            custom_text = defines.FLAKE_ERRORS_MAPPING.get(
                error.error_code, f'{error.error_code}-{error.text}')
            response.append(PyFlakeResponse(
                error_code=error.error_code,
                line_number=error.line_number,
                column=error.column,
                text=custom_text,
                physical_line=error.physical_line,
                solution_file_id=self._solution_file_id,
            ))
        return response

    def _get_errors_from_solution(self) -> typing.List[PyFlakeResponse]:
        errors = []
        index_of_check = 0
        with tempfile.NamedTemporaryFile('w') as temp_file:
            temp_file.write(self._code)
            temp_file.flush()

            self.app.run_checks([temp_file.name])
            results = self.app.file_checker_manager.checkers[
                index_of_check].results
            for result in results:
                response = PyFlakeResponse(
                    *result, solution_file_id=self._solution_file_id)
                errors.append(response)
        return errors
