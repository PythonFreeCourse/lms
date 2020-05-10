import os

import pytest

from lms.lmsdb import models
from lms.lmstests.public.unittests import import_tests
from lms.lmstests.public.unittests import executers
from lms.lmstests.public.unittests import tasks
from lms.tests import conftest

STUDENT_CODE = '''
def foo(bar=None):
    return 'bar' if bar == 'bar' else 'foo'
'''

EXERCISE_TESTS = os.path.join(conftest.SAMPLES_DIR, 'student_test_code.py')


class TestUTForExercise:
    def test_check_solution_with_exercise_process_stub(
            self, solution: models.Solution,
    ):
        self._initialize_solution(solution)
        self._run_unit_tests(solution.id)
        self._verify_comments()

    @pytest.mark.skip('Should run with docker system access')
    def test_check_solution_with_exercise_ut_full_docker(
            self, solution: models.Solution,
    ):
        self._initialize_solution(solution)
        self._run_unit_tests(
            solution.id, executers.DockerExecutor.executor_name(),
        )
        self._verify_comments()

    @staticmethod
    def _verify_comments():
        auto_comments = tuple(models.SolutionExerciseTestExecution.select())
        assert len(auto_comments) == 2
        first = auto_comments[0]
        assert first.exercise_test_name.test_name == 'test_check_bar_bar'
        assert first.exercise_test_name.pretty_test_name == 'שם כזה מגניב 2'
        expected = ('AssertionError: איזה ברברון '
                    "assert 'bar' == 'barbaron'   - bar   + barbaron")
        assert expected == first.user_message
        assert "foo('bar') == 'barbaron'" in first.staff_message

    @staticmethod
    def _initialize_solution(solution: models.Solution):
        solution.json_data_str = STUDENT_CODE
        solution.save()
        import_tests.load_test_from_module(EXERCISE_TESTS)

    @staticmethod
    def _run_unit_tests(solution_id, executor_name=None):
        if executor_name is None:
            executor_name = executers.SameProcessExecutor.executor_name()
        tasks.run_tests_for_solution(
            solution_id=solution_id,
            executor_name=executor_name,
        )
