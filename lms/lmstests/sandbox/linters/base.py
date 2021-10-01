import logging
import typing

from flask_babel import gettext as _  # type: ignore


class LinterError(typing.NamedTuple):
    error_code: str
    line_number: int
    column: int
    text: str
    physical_line: str
    solution_file_id: str


CANT_EXECUTE_CODE_MESSAGE = _("The automatic checker couldn't run your code.")


class BaseLinter:
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

    def _get_errors_from_solution(self) -> typing.Iterable[LinterError]:
        raise NotImplementedError

    @staticmethod
    def match_to_file_suffix(file_suffix: str) -> bool:
        raise NotImplementedError('match_to_file_suffix must be implemented')

    def initialize(self):
        """For special initializing code, please write it here"""
        pass

    @classmethod
    def get_match_linter(
            cls,
            logger: logging.Logger,
            code: str,
            file_suffix: str,
            solution_file_id: str,
    ) -> typing.Optional['BaseLinter']:
        for linter in cls.__subclasses__():
            if linter.match_to_file_suffix(file_suffix):
                return linter(
                    logger=logger,
                    code=code,
                    file_suffix=file_suffix,
                    solution_file_id=solution_file_id,
                )
        return None

    def get_error_text(self, error: LinterError) -> str:
        return error.text

    def _get_run_errors(self):
        try:
            return self._get_errors_from_solution()
        except Exception as error:  # noqa: E902
            self._logger.info(
                'Failed to check %s with linter %s',
                self._solution_file_id, self.__class__.__name__,
            )
            return [LinterError(
                error_code='-1',
                line_number=getattr(error, 'lineno', 0),
                column=getattr(error, 'offset', 0),
                text=CANT_EXECUTE_CODE_MESSAGE,
                physical_line='',
                solution_file_id=self._solution_file_id,
            )]

    def run_check(self) -> typing.Sequence[LinterError]:
        self._logger.info(
            'checks errors on solution file %s with linter %s',
            self._solution_file_id, self.__class__.__name__)

        response = []
        for error in self._get_run_errors():
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
