import inspect
import os
import sys
import importlib

from lms.lmsdb import models
from lms.utils.log import log


BASE_DIR = os.path.abspath(os.path.join(__file__, '../../../../../'))


def register_test_class(file_path: str, test_class):
    log.debug(f'Registering test class {test_class=}')
    subject = test_class.__doc__
    exercises = tuple(
        models.Exercise.filter(models.Exercise.subject == subject),
    )
    if not exercises:
        log.info(f'Failed to find exercises for {subject=}')
        raise SystemError

    with open(file_path, 'r') as file_reader:
        code = file_reader.read()

    for exercise in exercises:
        course = exercise.course
        log.info(f'Registering {test_class=} for {exercise=} of {course=}')
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
                    log.debug(f'Loading test from {os.path.join(root, file)}')
                    load_test_from_module(os.path.join(root, file))
    elif os.path.isfile(file_path):
        log.debug(f'Loading test from {file_path}')
        load_test_from_module(file_path)


def load_test_from_module(file_path: str):
    relative_path = os.path.relpath(file_path, BASE_DIR)
    response = importlib.import_module(
        relative_path.replace('.py', '').replace('/', '.'))
    for potential_test in inspect.getmembers(response):
        log.debug(f'Potential test: {potential_test}')
        potential_test = potential_test[0]
        potential_test_cls = getattr(response, potential_test)
        if potential_test.startswith('Test'):
            log.debug(f'Registering test class {potential_test}')
            register_test_class(file_path, potential_test_cls)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('python load_tests.py test-module-path')  # noqa: T201
        exit(-1)
    if not os.path.exists(sys.argv[1]):
        print(f"Path {sys.argv[1]} doesn't exists")  # noqa: T201
        exit(-1)
    if "-X" in sys.argv:
        log.configure(handlers=[{"sink": sys.stdout, "level": "DEBUG"}])
    load_tests_from_path(file_path=sys.argv[1])
