import pytest

from lms.lmsdb import models
from lms.lmstests.public.linters import tasks


class TestGenericLinter:
    @staticmethod
    def test_run_linters_expect_unknown_solution(
            solution: models.Solution, caplog: pytest.LogCaptureFixture,
    ):
        tasks.run_linter_on_solution(solution.id)
        assert 'does not exist' not in caplog.text
        assert 'failed to check' not in caplog.text

        nonexist_solution = 123456789
        with pytest.raises(models.Solution.DoesNotExist):
            tasks.run_linter_on_solution(nonexist_solution)
        assert 'does not exist' in caplog.text
        assert 'failed to check' not in caplog.text
