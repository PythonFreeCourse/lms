import os

import pytest

from lms.lmsdb import models
from lms.lmstests.public.unittests import import_tests
from lms.lmstests.public.unittests import executers
from lms.lmstests.public.unittests import tasks
from lms.models import notifications
from lms.tests import conftest


STUDENT_CODE = '''
def foo(bar=None):
    return 'bar' if bar == 'bar' else 'foo'
'''

EXERCISE_TESTS = os.path.join(conftest.SAMPLES_DIR, 'student_test_code.py')
INVALID_EXERCISE_TESTS = os.path.join(
    conftest.SAMPLES_DIR, 'not_working_test_code.py')
UNITTEST_NOTIFICATION = notifications.NotificationKind.UNITTEST_ERROR.value


class TestUTForExercise:
    def test_check_solution_with_exercise_process_stub(
            self, solution: models.Solution,
    ):
        self._initialize_solution(solution, EXERCISE_TESTS)
        self._run_unit_tests(solution.id)
        self._verify_comments()
        self._verify_notifications(solution)

    def test_check_solution_with_invalid_exercise(
            self, solution: models.Solution,
    ):
        self._initialize_solution(solution, INVALID_EXERCISE_TESTS)
        self._run_unit_tests(solution.id)
        auto_comments = tuple(models.SolutionExerciseTestExecution.select())
        assert len(auto_comments) == 1
        comment = auto_comments[0]

        expected_name = models.ExerciseTestName.FATAL_TEST_NAME
        assert comment.exercise_test_name.test_name == expected_name
        expected_name = models.ExerciseTestName.FATAL_TEST_PRETTY_TEST_NAME
        assert comment.exercise_test_name.pretty_test_name == expected_name

        all_notifications = list(notifications.get(user=solution.solver))
        assert len(all_notifications) == 1
        assert all_notifications[0].kind == UNITTEST_NOTIFICATION

    @pytest.mark.skip('Should run with docker system access')
    def test_check_solution_with_exercise_ut_full_docker(
            self, solution: models.Solution,
    ):
        self._initialize_solution(solution, EXERCISE_TESTS)
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
    def _verify_notifications(solution):
        all_notifications = notifications.get(user=solution.solver)
        assert len(all_notifications) == 1
        assert all_notifications[0].kind == UNITTEST_NOTIFICATION

    @staticmethod
    def _initialize_solution(solution: models.Solution, module_name: str):
        solution.json_data_str = STUDENT_CODE
        solution.save()
        import_tests.load_test_from_module(module_name)

    @staticmethod
    def _run_unit_tests(solution_id, executor_name=None):
        if executor_name is None:
            executor_name = executers.SameProcessExecutor.executor_name()
        tasks.run_tests_for_solution(
            solution_id=solution_id,
            executor_name=executor_name,
        )
