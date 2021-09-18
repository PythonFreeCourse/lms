import datetime

from lms.lmsdb.models import Course, Exercise, User
from tests import conftest


class TestExercise:
    def test_due_date(self, exercise: Exercise):
        assert exercise.open_for_new_solutions()
        exercise.is_archived = True
        exercise.save()
        assert not exercise.open_for_new_solutions()

        exercise.is_archived = False
        later_due_date = datetime.datetime.now() - datetime.timedelta(hours=1)
        exercise.due_date = later_due_date
        exercise.save()
        assert not exercise.open_for_new_solutions()

        after_due_date = datetime.datetime.now() + datetime.timedelta(hours=1)
        exercise.due_date = after_due_date
        exercise.save()
        assert exercise.open_for_new_solutions()

    @staticmethod
    def test_courses_exercises(course: Course, student_user: User):
        course2 = conftest.create_course(index=1)
        conftest.create_usercourse(student_user, course)
        conftest.create_exercise(course2, 1)
        assert len(list(Exercise.get_objects(student_user.id))) == 0

        conftest.create_exercise(course, 1, index=1)
        assert len(list(Exercise.get_objects(student_user.id))) == 1
