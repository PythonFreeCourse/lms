import inspect
import os
import typing
import sys
import importlib
import logging

from lms.lmsdb import models

logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(__file__, '../../../../../'))


def register_test_class(file_path: str, test_class: typing.ClassVar):
    subject = test_class.__doc__
    exercise = models.Exercise.get_or_none(models.Exercise.subject == subject)
    if not exercise:
        _logger.info('Failed to find exercise subject %s', subject)
        raise SystemError

    with open(file_path, 'r') as file_reader:
        code = file_reader.read()

    exercise_test = models.ExerciseTest.get_or_create_exercise_test(
        exercise=exercise,
        code=code,
    )

    for test_func_name in inspect.getmembers(test_class):
        test_func_name = test_func_name[0]
        if test_func_name.startswith('test_'):
            test_func = getattr(test_class, test_func_name)
            models.ExerciseTestName.create_exercise_test_name(
                exercise_test=exercise_test,
                test_name=test_func_name,
                pretty_test_name=test_func.__doc__,
            )


def load_test_from_module(file_path: str):
    relative_path = os.path.relpath(file_path, BASE_DIR)
    response = importlib.import_module(
        relative_path.replace('.py', '').replace('/', '.'))
    for potential_test in inspect.getmembers(response):
        potential_test = potential_test[0]
        potential_test_cls = getattr(response, potential_test)
        if potential_test.startswith('Test'):
            register_test_class(file_path, potential_test_cls)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('python load_tests.py test-module-path')  # noqa: T001
    load_test_from_module(file_path=sys.argv[1])
