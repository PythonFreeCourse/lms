from lms.lmsdb import models
from lms.lmstests.public.linters import tasks


INVALID_CODE = 's1\n'
INVALID_CODE_MESSAGE = "Found unparsable section: 's1'"

VALID_CODE = 'SELECT 1\n'


class TestSQLLinter:
    def test_invalid_solution(self, solution: models.Solution):
        solution_file = solution.solution_files.get()
        solution_file.path = 'sql.sql'
        solution_file.code = INVALID_CODE
        solution_file.save()
        tasks.run_linter_on_solution(solution.id)
        comments = tuple(models.Comment.by_solution(solution))
        assert comments
        assert len(comments) == 1
        assert comments[0].comment.text == INVALID_CODE_MESSAGE

    def test_valid_solution(self, solution: models.Solution):
        solution_file = solution.solution_files.get()
        solution_file.path = 'sql.sql'
        solution_file.code = VALID_CODE
        solution_file.save()
        tasks.run_linter_on_solution(solution.id)
        comments = tuple(models.Comment.by_solution(solution))
        assert not comments
