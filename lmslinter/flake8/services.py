import typing
import tempfile

from flake8.main import application

from lmsdb import models


class PyFlakeResponse(typing.NamedTuple):
    error_code: str
    line_number: int
    column: int
    text: str
    physical_line: str


FLAKE_ERRORS_MAPPING = {
    'Q000': 'השתמש בצוקואים בודדים ולא בגרשיים'
}

FLAKE_SKIP_ERRORS = (
    'T001',  # print found
    'W292',  # no new line in the end of the code
)


class PyFlakeChecker:
    def __init__(self, solution_check_pk: str, logger):
        self.solution_check_pk = solution_check_pk
        self._app = None
        self._solution = None
        self._logger = logger

    def initialize(self):
        self._app = application.Application()
        self._app.initialize(argv=[])
        self._solution = models.Solution.get_by_id(self.solution_check_pk)

    @property
    def app(self) -> application.Application:
        return self._app

    @property
    def solution(self) -> models.Solution:
        return self._solution

    def run_check(self):
        self._logger.info("checks errors on solution %s", self.solution_check_pk)
        errors = self._get_errors_from_solution()

        for error in errors:
            if error.error_code in FLAKE_SKIP_ERRORS:
                self._logger.info("Skipping error %s to solution %s", error, self.solution_check_pk)
                continue

            self._logger.info("Adding error %s to solution %s", error,  self.solution_check_pk)
            text = FLAKE_ERRORS_MAPPING.get(error.error_code, f"{error.error_code}-{error.text}")
            comment, _ = models.CommentText.get_or_create(text=text)
            models.Comment.create(
                commenter=models.User.get_system_user(),
                line_number=error.line_number,
                comment=comment,
                solution=self.solution
            )

    def _get_errors_from_solution(self) -> typing.List[PyFlakeResponse]:
        errors = []
        code_content = self.solution.code
        index_of_check = 0
        with tempfile.NamedTemporaryFile("w") as temp_file:
            temp_file.write(code_content)
            temp_file.flush()

            self.app.run_checks([temp_file.name])
            raw_results = self.app.file_checker_manager.checkers[index_of_check].results
            for result in raw_results:
                # yes, a library of types cannot use named tuples, thanks flake8
                errors.append(PyFlakeResponse(*result))
        return errors
