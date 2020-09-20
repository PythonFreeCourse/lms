import os

import pytest

from lms.lmsdb import models
from lms.lmstests.public.linters import tasks


INVALID_CODE = '<html>'
INVALID_CODE_MESSAGES = {
    'Start tag seen without seeing a doctype first. Expected “<!DOCTYPE html>”.',
    'Element “head” is missing a required instance of child element “title”.',
    'Consider adding a “lang” attribute to the “html” start tag to declare the language of this document.',
}

VALID_CODE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Title</title>
</head>
<body>
</body>
</html>
'''


@pytest.mark.skipif(
    condition=os.system('which vnu') != 0,  # noqa: S605,S607
    reason='should run with VNU linter in path. see VNULinter class for more information',
)
class TestHTMLLinter:
    def test_invalid_solution(self, solution: models.Solution):
        solution_file = solution.solution_files.get()
        solution_file.path = 'index.html'
        solution_file.code = INVALID_CODE
        solution_file.save()
        tasks.run_linter_on_solution(solution.id)
        comments = tuple(models.Comment.by_solution(solution))
        assert comments
        assert len(comments) == 3
        comment_texts = {comment.comment.text for comment in comments}
        assert comment_texts == INVALID_CODE_MESSAGES

    def test_valid_solution(self, solution: models.Solution):
        solution_file = solution.solution_files.get()
        solution_file.path = 'index.html'
        solution_file.code = VALID_CODE
        solution_file.save()
        tasks.run_linter_on_solution(solution.id)
        comments = tuple(models.Comment.by_solution(solution))
        assert not comments
