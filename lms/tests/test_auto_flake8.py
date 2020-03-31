from lms.lmsdb import models
from lms.lmstests.flake8 import tasks

INVALID_CODE = 'print("Hello Word")'
INVALID_CODE_MESSAGE = 'השתמש בצוקואים בודדים ולא בגרשיים'
VALID_CODE = 'print(0)'


class TestAutoFlake8:
    def test_invalid_solution(self, solution: models.Solution):
        solution.json_data_str = INVALID_CODE
        solution.save()
        tasks.run_flake8_on_solution(solution.id)
        comments = tuple(models.Comment.filter(models.Comment.solution == solution))
        assert comments
        assert len(comments) == 1
        comment_text = comments[0].comment.text
        assert comment_text == INVALID_CODE_MESSAGE

    def test_valid_solution(self, solution: models.Solution):
        solution.json_data_str = VALID_CODE
        solution.save()
        tasks.run_flake8_on_solution(solution.id)
        comments = tuple(models.Comment.filter(models.Comment.solution == solution))
        assert not comments
