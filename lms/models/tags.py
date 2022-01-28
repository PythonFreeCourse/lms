from typing import Iterable, Union

from lms.lmsdb.models import Exercise, ExerciseTag, Tag


def get_exercises_of(
    course_id: int, tag_name: str,
) -> Union[Iterable['ExerciseTag'], 'ExerciseTag']:
    return (
        ExerciseTag
        .select(ExerciseTag.exercise)
        .join(Tag)
        .where(Tag.text == tag_name, Tag.course == course_id)
    )


def by_exercise_id(
    exercise_id: int,
) -> Union[Iterable['ExerciseTag'], 'ExerciseTag']:
    return ExerciseTag.select().where(ExerciseTag.exercise == exercise_id)


def by_course(course: int) -> Union[Iterable['ExerciseTag'], 'ExerciseTag']:
    return ExerciseTag.select().join(Exercise).where(Exercise.course == course)


def by_exercise_number(
    course: int, number: int,
) -> Union[Iterable['ExerciseTag'], 'ExerciseTag']:
    return by_course(course).where(Exercise.number == number)
