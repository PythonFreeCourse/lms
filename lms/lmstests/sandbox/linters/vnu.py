import json
import subprocess  # noqa S404
import tempfile
import typing

from lms.lmstests.sandbox.linters import defines
from lms.lmstests.sandbox.linters.base import BaseLinter, LinterError


class VNULinter(BaseLinter):
    """
    This linter based on installed execute vnu.
    This package installed in our lms/Dockerfile
    See https://github.com/validator/validator
    """

    supported_files = ('html', 'htm', 'css')

    def get_error_text(self, error: LinterError) -> str:
        return defines.VNU_ERRORS_MAPPING.get(error.text, error.text)

    @staticmethod
    def match_to_file_suffix(file_suffix: str) -> bool:
        return file_suffix.lower() in VNULinter.supported_files

    def _get_errors_from_solution(self) -> typing.Iterable[LinterError]:
        results = self._execute_vnu_command()

        for result in results['messages']:
            line = result.get('firstline') or result.get('lastLine')
            if not line:  # set default line in case of empty element
                line = 1

            try:
                response = LinterError(
                    error_code=result['type'],
                    line_number=line,
                    column=result['firstColumn'],
                    text=result['message'],
                    physical_line=result['extract'],
                    solution_file_id=self._solution_file_id,
                )
            except KeyError:
                self._logger.warning('failed to parse error, continue...')
                continue

            if response.text in defines.VNU_SKIP_ERROR_MESSAGES:
                self._logger.info(
                    'Skipping error %s on line %s to solution file %s',
                    response.error_code,
                    response.line_number,
                    self._solution_file_id,
                )
            else:
                yield response

    def _execute_vnu_command(self) -> typing.Dict:
        with tempfile.NamedTemporaryFile(
                'w', suffix=self._file_suffix) as temp_file:
            temp_file.write(self._code)
            temp_file.flush()
            process = subprocess.Popen(  # noqa: S603
                args=(
                    'vnu',
                    '--format',
                    'json',
                    '--also-check-css',
                    temp_file.name,
                ),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            output_buffer, error_buffer = process.communicate()
        results = json.loads(error_buffer)
        return results
