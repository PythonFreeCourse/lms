import inspect
import os
import typing
import sys
import importlib

from lms.lmsdb import models
from lms.utils.log import log


BASE_DIR = os.path.abspath(os.path.join(__file__, '../../../../../'))


def register_test_class(file_path: str, test_class: typing.ClassVar):
    subject = test_class.__doc__
    exercise = models.Exercise.get_or_none(models.Exercise.subject == subject)
    if not exercise:
        log.info(f'Failed to find exercise subject {subject}')
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


def load_tests_from_path(file_path: str):
    if os.path.isdir(file_path):
        for root, _, files in os.walk(file_path):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    load_test_from_module(os.path.join(root, file))
    elif os.path.isfile(file_path):
        load_test_from_module(file_path)


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
    load_tests_from_path(file_path=sys.argv[1])
