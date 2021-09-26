from lms.lmsdb.models import Comment, Solution
from lms.lmstests.public.linters import tasks


INVALID_CODE = 's1\n'
INVALID_CODE_MESSAGE = (
    'Line 1, Position 1: Found unparsable section: &#x27;s1&#x27;'  # Escape
)

VALID_CODE = 'SELECT 1\n'


class TestSQLLinter:
    def test_invalid_solution(self, solution: Solution):
        solution_file = solution.solution_files.get()
        solution_file.path = 'sql.sql'
        solution_file.code = INVALID_CODE
        solution_file.save()
        tasks.run_linter_on_solution(solution.id)
        comments = tuple(Comment.by_solution(solution))
        assert comments
        assert len(comments) == 1
        assert comments[0].comment.text == INVALID_CODE_MESSAGE

    def test_valid_solution(self, solution: Solution):
        solution_file = solution.solution_files.get()
        solution_file.path = 'sql.sql'
        solution_file.code = VALID_CODE
        solution_file.save()
        tasks.run_linter_on_solution(solution.id)
        comments = tuple(Comment.by_solution(solution))
        assert not comments
