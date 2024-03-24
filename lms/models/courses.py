from typing import NamedTuple

from lms.lmsdb.models import Course, User


def get_students(course_id: int) -> NamedTuple:
    fields = [User.id, User.username, User.fullname, Course.name]
    course = Course.get_by_id(course_id)
    return course.get_students(fields=fields).namedtuples()
