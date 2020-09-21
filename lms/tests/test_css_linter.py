import os

import pytest

from lms.lmsdb import models
from lms.lmstests.public.linters import tasks


INVALID_CODE = '''
 main {
   display: pita;
 }
'''
INVALID_CODE_MESSAGES = 'CSS: “display”: “pita” is not a “display” value.'

VALID_CODE = '''
 main {
   display: flex;
 }
'''


@pytest.mark.skipif(
    condition=os.system('which vnu') != 0,  # noqa: S605,S607
    reason='should run with VNU linter in path. see VNULinter class for more information',
)
class TestCSSLinter:
    def test_invalid_solution(self, solution: models.Solution):
        solution_file = solution.solution_files.get()
        solution_file.path = 'index.css'
        solution_file.code = INVALID_CODE
        solution_file.save()
        tasks.run_linter_on_solution(solution.id)
        comments = tuple(models.Comment.by_solution(solution))
        assert comments
        assert len(comments) == 1
        assert comments[0].comment.text == INVALID_CODE_MESSAGES

    def test_valid_solution(self, solution: models.Solution):
        solution_file = solution.solution_files.get()
        solution_file.path = 'index.css'
        solution_file.code = VALID_CODE
        solution_file.save()
        tasks.run_linter_on_solution(solution.id)
        comments = tuple(models.Comment.by_solution(solution))
        assert not comments
