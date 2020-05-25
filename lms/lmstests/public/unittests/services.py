import logging
import typing

import junitparser

from lms.lmsdb import models
from lms.lmstests.public.unittests import executers


class UnitTestChecker:
    def __init__(
            self,
            logger: logging.Logger,
            solution_id: str,
            executor_name: str,
    ):
        self._logger = logger
        self._solution_id = solution_id
        self._executor_name = executor_name
        self._solution: typing.Optional[models.Solution] = None
        self._exercise_auto_test: typing.Optional[models.ExerciseTest] = None

    def initialize(self):
        self._solution = models.Solution.get_by_id(self._solution_id)
        self._exercise_auto_test = models.ExerciseTest.get_by_exercise(
            exercise=self._solution.exercise,
        )

    def run_check(self) -> None:
        self._logger.info('start run_check on solution %s', self._solution_id)
        if self._exercise_auto_test is None:
            self._logger.info('No UT for solution %s', self._solution_id)
            return
        junit_results = self._run_tests_on_solution()
        self._populate_junit_results(junit_results)
        self._logger.info('end run_check solution %s', self._solution_id)

    def _run_tests_on_solution(self):
        self._logger.info('start UT on solution %s', self._solution_id)
        python_code = self._generate_python_code()
        python_file = 'test_checks.py'
        test_output_path = 'output.xml'

        junit_results = None
        try:
            with executers.get_executor(self._executor_name) as executor:
                executor.write_file(python_file, python_code)
                executor.run_on_executor(
                    args=(
                        'pytest',
                        executor.get_file_path(python_file),
                        '--junitxml',
                        executor.get_file_path(test_output_path)),
                )
                junit_results = executor.get_file(file_path=test_output_path)
        except Exception:
            self._logger.exception('Failed to run tests on solution %s',
                                   self._solution_id)
        self._logger.info('end UT on solution %s', self._solution_id)
        return junit_results

    def _generate_python_code(self) -> str:
        user_code = self._solution.code
        test_code = self._exercise_auto_test.code
        return f'{test_code}\n\n{user_code}'

    def _populate_junit_results(self, junit_results: str):
        results = None
        if junit_results:
            results = junitparser.TestSuite.fromstring(junit_results)
        if not results:
            self._logger.info('junit invalid results (%s) on solution %s',
                              junit_results, self._solution_id)
            models.SolutionExerciseTestExecution.create_execution_result(
                solution=self._solution,
                test_name=models.ExerciseTestName.FATAL_TEST_NAME,
                user_message='אנא פנו לסגל',
                staff_message='אחי, בדקת את הקוד שלך?',
            )
            return

        for case in results:
            result = case.result
            if result is None:
                self._logger.info(
                    'case %s passed for solution %s',
                    case.name, self._solution,
                )
                continue
            # invalid case
            message = '\n'.join([elem[1] for elem in result._elem.items()])
            self._logger.info('crate comment on test %s solution %s',
                              case.name, self._solution_id)
            models.SolutionExerciseTestExecution.create_execution_result(
                solution=self._solution,
                test_name=case.name,
                user_message=message,
                staff_message=result._elem.text,
            )
