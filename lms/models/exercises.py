from typing import Optional

from lms.lmsdb.models import Exercise


def get_basic_exercises_view(course_id: Optional[int]):
    fields = [
        Exercise.id, Exercise.number,
        Exercise.subject.alias('name'), Exercise.is_archived,
    ]
    query = Exercise.select(*fields)
    if course_id is not None:
        query = query.where(Exercise.course == course_id)
    return query.namedtuples()
