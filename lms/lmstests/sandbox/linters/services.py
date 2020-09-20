import json
import logging
import tempfile
import typing
import subprocess

from flake8.main import application

from lms.lmstests.sandbox.linters import defines


class LinterError(typing.NamedTuple):
    error_code: str
    line_number: int
    column: int
    text: str
    physical_line: str
    solution_file_id: str


class BaseLinter:
    error_codes_whitelist = ()

    def __init__(
            self,
            logger: logging.Logger,
            code: str,
            file_suffix: str,
            solution_file_id: str,
    ):
        self._app = None
        self._code = code
        self._file_suffix = file_suffix
        self._logger = logger
        self._solution_file_id = solution_file_id

    def _get_errors_from_solution(self) -> typing.List[LinterError]:
        raise NotImplementedError

    @staticmethod
    def match_to_file_suffix(file_suffix: str) -> bool:
        raise NotImplementedError

    def initialize(self):
        """
        For special initializing code, please write it here
        """

    @classmethod
    def get_match_linter(
            cls,
            logger: logging.Logger,
            code: str,
            file_suffix: str,
            solution_file_id: str,
    ) -> 'BaseLinter':
        for linter in cls.__subclasses__():
            if linter.match_to_file_suffix(file_suffix):
                return linter(
                    logger=logger,
                    code=code,
                    file_suffix=file_suffix,
                    solution_file_id=solution_file_id,
                )

    def get_error_text(self, error: LinterError):
        return error.text

    def run_check(self) -> typing.Sequence[LinterError]:
        self._logger.info(
            'checks errors on solution file %s with linter %s',
            self._solution_file_id, self.__class__.__name__)
        errors = self._get_errors_from_solution()
        response = []
        for error in errors:
            if error.error_code in self.error_codes_whitelist:
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
            custom_text = self.get_error_text(error)
            response.append(LinterError(
                error_code=error.error_code,
                line_number=error.line_number,
                column=error.column,
                text=custom_text,
                physical_line=error.physical_line,
                solution_file_id=self._solution_file_id,
            ))
        return response


class PythonLinter(BaseLinter):
    error_codes_whitelist = defines.FLAKE_SKIP_ERRORS

    def initialize(self):
        self._app = application.Application()
        self._app.initialize(argv=['--import-order-style', 'google'])

    @property
    def app(self) -> application.Application:
        return self._app

    def get_error_text(self, error: LinterError):
        default_text = f'{error.error_code}-{error.text}'
        return defines.FLAKE_ERRORS_MAPPING.get(error.error_code, default_text)

    @staticmethod
    def match_to_file_suffix(file_suffix: str) -> bool:
        return file_suffix.lower() == 'py'

    def _get_errors_from_solution(self) -> typing.List[LinterError]:
        errors = []
        index_of_check = 0
        with tempfile.NamedTemporaryFile('w') as temp_file:
            temp_file.write(self._code)
            temp_file.flush()

            self.app.run_checks([temp_file.name])
            results = self.app.file_checker_manager.checkers[
                index_of_check].results
            for result in results:
                response = LinterError(
                    *result, solution_file_id=self._solution_file_id)
                errors.append(response)
        return errors


class VNULinter(BaseLinter):
    error_codes_whitelist = defines.VNU_SKIP_ERRORS
    supported_files = ('html', 'htm')

    def get_error_text(self, error: LinterError):
        default_text = f'{error.error_code}-{error.text}'
        return defines.VNU_ERRORS_MAPPING.get(error.error_code, default_text)

    @staticmethod
    def match_to_file_suffix(file_suffix: str) -> bool:
        return file_suffix.lower() in self.supported_files

    def _get_errors_from_solution(self) -> typing.List[LinterError]:
        errors = []
        with tempfile.NamedTemporaryFile(
                'w', suffix=self._file_suffix) as temp_file:
            temp_file.write(self._code)
            temp_file.flush()
            process = subprocess.Popen(
                args=(
                    'vnu',
                    '--format',
                    'json',
                    temp_file.name,
                ),
                stdout=subprocess.PIPE,
            )
            output_buffer, error_buffer = process.communicate()
            results = json.loads(error_buffer)
            for result in results['messages']:
                try:
                    response = LinterError(
                        error_code=result['type'],
                        line_number=result['firstline'],
                        column=result['firstColumn'],
                        text=result['message'],
                        physical_line=result['extract'],
                        solution_file_id=self._solution_file_id,
                    )
                    errors.append(response)
                except KeyError:
                    self._logger.info('failed to parse error, continue...')
        return errors
