from typing import List, Optional, Tuple

from werkzeug.datastructures import FileStorage

from lms.extractors.base import Extractor, File
from lms.lmsdb.models import Exercise, Solution, User
from lms.models.errors import UploadError


def _is_uploaded_before(user: User, file: FileStorage) -> bool:
    saved_location = file.tell()
    file.seek(0)
    is_duplicate = Solution.is_duplicate(file.read(), user)
    file.seek(saved_location)
    return is_duplicate


def _create_new_solution(
        exercise_id: int,
        user: User,
        files: List[File],
        hashed: Optional[str] = None,
) -> bool:
    exercise = Exercise.get_or_none(exercise_id)
    if exercise is None:
        raise UploadError(f'No such exercise id: {exercise_id}')
    elif not exercise.open_for_new_solutions():
        raise UploadError(
            f'Exercise {exercise_id} is closed for new solutions.')
    elif not files:
        raise UploadError(f'There are no files to upload for {exercise_id}.')

    return Solution.create_solution(
        exercise=exercise,
        solver=user,
        files=files,
        hashed=hashed,
    )


def new(user: User, file: FileStorage) -> Tuple[List[int], List[int]]:
    if not _is_uploaded_before(user, file):
        raise UploadError('You try to reupload an old solution.')

    matches: List[int] = []
    misses: List[int] = []
    for exercise_id, files in Extractor(file):
        try:
            _create_new_solution(exercise_id, user, files)
        except UploadError:
            misses.append(exercise_id)

    return matches, misses
