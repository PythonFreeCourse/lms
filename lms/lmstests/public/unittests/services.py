import logging
import subprocess  # noqa: S404
from typing import Iterable, List, Optional, Tuple

from flask_babel import gettext as _  # type: ignore
import junitparser
from junitparser.junitparser import TestCase

from lms.lmsdb import models
from lms.lmstests.public.unittests import executers
from lms.lmsweb import routes
from lms.models import notifications


NumberOfErrors = int
CANT_EXECUTE_CODE_MESSAGE = _("The automatic checker couldn't run your code.")


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
        self._solution: Optional[models.Solution] = None
        self._exercise_auto_test: Optional[models.ExerciseTest] = None

    def initialize(self):
        self._solution = models.Solution.get_by_id(self._solution_id)
        self._exercise_auto_test = models.ExerciseTest.get_by_exercise(
            exercise=self._solution.exercise,
        )

    def run_check(self) -> None:
        assert self._solution is not None
        self._logger.info('start run_check on solution %s', self._solution_id)
        if self._exercise_auto_test is None:
            self._logger.info('No UT for solution %s', self._solution_id)
            return
        junit_results = self._run_tests_on_solution()
        self._populate_junit_results(junit_results.encode('utf-8'))
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
                pyfile_path = executor.get_file_path(python_file)
                test_output_path = executor.get_file_path(test_output_path)
                args = ('pytest', pyfile_path, '--junitxml', test_output_path)
                executor.run_on_executor(args=args)
                junit_results = executor.get_file(file_path=test_output_path)
        except (IOError, subprocess.CalledProcessError):  # NOQA: B902
            self._logger.exception(
                'Failed to run tests on solution %s', self._solution_id,
            )
            return ''
        self._logger.info('end UT on solution %s', self._solution_id)
        return junit_results

    def _generate_python_code(self) -> str:
        # FIX: Multiple files
        assert self._solution is not None
        user_code = '\n'.join(
            file.code for file in self._solution.solution_files
        )
        assert self._exercise_auto_test is not None
        test_code = self._exercise_auto_test.code
        return f'{test_code}\n\n{user_code}'

    def _get_parsed_suites(
            self, raw_results: bytes,
    ) -> Optional[Iterable[junitparser.TestSuite]]:
        try:
            parsed_string = junitparser.TestSuite.fromstring(raw_results)
            return parsed_string.testsuites()
        except SyntaxError:  # importing xml make the lint go arrrr
            self._logger.exception('Failed to parse junit result')
            return None
        except junitparser.JUnitXmlError as error:
            self._logger.exception(
                'Failed to parse junit result because %s', error,
            )
            return None

    def _populate_junit_results(self, raw_results: bytes) -> None:
        assert self._solution is not None  # noqa: S101
        if not raw_results:
            return None

        suites = self._get_parsed_suites(raw_results)
        if not suites:
            return None

        tests_ran = False
        number_of_failures = 0
        for test_suite in suites:
            failures, ran = self._handle_test_suite(test_suite)
            number_of_failures += failures
            if ran and not tests_ran:
                tests_ran = ran

        if not tests_ran:
            self._handle_failed_to_execute_tests(raw_results)
            return None

        if not number_of_failures:
            return None

        fail_message = _(
            'The automatic checker failed in %(number)d examples in your '
            '"%(subject)s" solution.',
            number=number_of_failures,
            subject=self._solution.exercise.subject,
        )
        notifications.send(
            kind=notifications.NotificationKind.UNITTEST_ERROR,
            user=self._solution.solver,
            related_id=self._solution.id,
            message=fail_message,
            action_url=f'{routes.SOLUTIONS}/{self._solution_id}',
        )

    def _handle_failed_to_execute_tests(self, raw_results: bytes) -> None:
        self._logger.info(b'junit invalid results (%s) on solution %s',
                          raw_results, self._solution_id)
        fail_user_message = CANT_EXECUTE_CODE_MESSAGE
        models.SolutionExerciseTestExecution.create_execution_result(
            solution=self._solution,
            test_name=models.ExerciseTestName.FATAL_TEST_NAME,
            user_message=fail_user_message,
            staff_message=_('Bro, did you check your code?'),
        )
        notifications.send(
            kind=notifications.NotificationKind.UNITTEST_ERROR,
            user=self._solution.solver,
            related_id=self._solution.id,
            message=fail_user_message,
            action_url=f'{routes.SOLUTIONS}/{self._solution_id}',
        )

    def _handle_result(
            self, case_name: str, result: junitparser.Element,
    ) -> None:
        message = ' '.join(
            elem[1].replace('\n', '')
            for elem in result._elem.items()
        )
        self._logger.info(
            'Create comment on test %s solution %s.',
            case_name, self._solution_id,
        )
        models.SolutionExerciseTestExecution.create_execution_result(
            solution=self._solution,
            test_name=case_name,
            user_message=message,
            staff_message=result.text,
        )

    def _handle_test_case(self, case: TestCase) -> NumberOfErrors:
        results: List[junitparser.Element] = case.result
        if not results:
            self._logger.info(
                'Case %s passed for solution %s.',
                case.name, self._solution,
            )
            return False

        number_of_failures = 0
        for result in results:
            self._handle_result(case.name, result)
            number_of_failures += 1
        return number_of_failures

    def _handle_test_suite(
            self, test_suite: junitparser.TestSuite,
    ) -> Tuple[int, bool]:
        number_of_failures = 0
        tests_ran = False
        for case in test_suite:
            tests_ran = True
            number_of_failures += int(self._handle_test_case(case))
        return number_of_failures, tests_ran
