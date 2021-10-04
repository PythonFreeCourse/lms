from typing import List, Optional, Tuple, Union

from werkzeug.datastructures import FileStorage

from lms.extractors.base import Extractor, File
from lms.lmsdb.models import Exercise, Solution, User
from lms.lmstests.public.identical_tests import tasks as identical_tests_tasks
from lms.lmstests.public.linters import tasks as linters_tasks
from lms.lmstests.public.unittests import tasks as unittests_tasks
from lms.models.errors import AlreadyExists, UploadError
from lms.lmsweb import config
from lms.utils.log import log


def _is_uploaded_before(
    user: User,
    exercise: Exercise,
    file_hash: str,
) -> bool:
    return Solution.is_duplicate(
        file_hash, user, exercise, already_hashed=True,
    )


def _upload_to_db(
        exercise_number: int,
        course_id: int,
        user_id: int,
        files: List[File],
        solution_hash: Optional[str] = None,
) -> Solution:
    exercise = Exercise.get_or_none(course=course_id, number=exercise_number)
    user = User.get_by_id(user_id)
    if exercise is None:
        raise UploadError(f'No such exercise id: {exercise_number}')
    elif not user.has_course(course_id):
        raise UploadError(
            f'Exercise {exercise_number} is invalid for this user.',
        )
    elif not exercise.open_for_new_solutions():
        raise UploadError(
            f'Exercise {exercise_number} is closed for new solutions.')

    if solution_hash and _is_uploaded_before(user, exercise, solution_hash):
        raise AlreadyExists('You try to reupload an old solution.')
    elif not files:
        raise UploadError(
            f'There are no files to upload for {exercise_number}.',
        )

    return Solution.create_solution(
        exercise=exercise,
        solver=user,
        files=files,
        hash_=solution_hash,
    )


def _run_auto_checks(solution: Solution) -> None:
    linters_tasks.run_linter_on_solution.apply_async(args=(solution.id,))
    unittests_tasks.run_tests_for_solution.apply_async(args=(solution.id,))
    if config.FEATURE_FLAG_CHECK_IDENTICAL_CODE_ON:
        check_ident = identical_tests_tasks.solve_solution_with_identical_code
        check_ident.apply_async(args=(solution.id,))


def new(
    user_id: int, course_id: int, file: FileStorage,
) -> Tuple[List[int], List[int]]:
    matches: List[int] = []
    misses: List[int] = []
    errors: List[Union[UploadError, AlreadyExists]] = []
    for exercise_number, files, solution_hash in Extractor(file):
        try:
            upload_solution(
                course_id=course_id,
                exercise_number=exercise_number,
                files=files,
                solution_hash=solution_hash,
                user_id=user_id,
            )
        except (UploadError, AlreadyExists) as e:
            log.debug(e)
            errors.append(e)
            misses.append(exercise_number)
        else:
            matches.append(exercise_number)

    if not matches and errors:
        raise UploadError(errors)

    return matches, misses


def upload_solution(
        course_id: int,
        exercise_number: int,
        files: List[File],
        solution_hash: str,
        user_id: int,
):
    solution = _upload_to_db(
        exercise_number=exercise_number,
        course_id=course_id,
        user_id=user_id,
        files=files,
        solution_hash=solution_hash,
    )
    _run_auto_checks(solution)
