from typing import Iterable, Optional, Union

from lms.lmsdb.models import Course, Exercise, ExerciseTag, Tag


def get_exercises_of(
    course: Course, tag_name: str,
) -> Union[Iterable['ExerciseTag'], 'ExerciseTag']:
    return (
        ExerciseTag
        .select(ExerciseTag.exercise)
        .join(Tag)
        .where(Tag.text == tag_name, Tag.course == course)
    )


def of_exercise(
    exercise_id: Optional[int] = None, course: Optional[int] = None,
    number: Optional[int] = None,
) -> Optional[Union[Iterable['ExerciseTag'], 'ExerciseTag']]:
    if exercise_id is not None:
        return ExerciseTag.select().where(ExerciseTag.exercise == id)
    elif course is not None:
        tags = (
            ExerciseTag
            .select()
            .join(Exercise)
            .where(Exercise.course == course)
        )
        if number is not None:
            tags = tags.where(Exercise.number == number)
        return tags
    return None
