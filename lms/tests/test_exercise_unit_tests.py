import pytest

from lms.lmsdb import models
from lms.lmstests.public.unittests import executers
from lms.lmstests.public.unittests import tasks

STUDENT_CODE = '''
def foo(bar=None):
    return 'bar' if bar == 'bar' else 'foo'
'''

STUDENT_CODE_TESTS = '''
class TestStudent:
    def test_check_foo_foo(self):
        assert foo() == 'foo'

    def test_check_bar_bar(self):
        assert foo('bar') == 'barbaron', 'איזה ברברון'

    def test_check_foo_bar_foo(self):
        assert foo() == 'foofoon'
'''


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
        assert first.test_name == 'test_check_bar_bar'
        assert 'איזה ברברון' in first.user_message
        assert "foo('bar') == 'barbaron'" in first.staff_message

    @staticmethod
    def _initialize_solution(solution: models.Solution):
        solution.json_data_str = STUDENT_CODE
        solution.save()
        models.ExerciseTest.create_exercise_test(
            exercise=solution.exercise,
            code=STUDENT_CODE_TESTS,
        )

    @staticmethod
    def _run_unit_tests(solution_id, executor_name=None):
        if executor_name is None:
            executor_name = executers.SameProcessExecutor.executor_name()
        tasks.run_tests_for_solution(
            solution_id=solution_id,
            executor_name=executor_name,
        )
