import datetime

from lms.lmsdb.models import Course, Exercise, User
from lms.models import exercises
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
    def test_courses_exercises(
        course: Course, student_user: User, captured_templates,
    ):
        course2 = conftest.create_course(index=1)
        conftest.create_usercourse(student_user, course)
        conftest.create_exercise(course2, 1)
        conftest.create_exercise(course2, 2)
        assert len(list(
            Exercise.get_objects(student_user.id, from_all_courses=True),
        )) == 0

        client = conftest.get_logged_user(username=student_user.username)
        client.get(f'course/{course.id}')
        template, _ = captured_templates[-1]
        assert template.name == 'exercises.html'
        conftest.create_exercise(course, 1, index=1)
        assert len(list(Exercise.get_objects(student_user.id))) == 1

        unregistered_response = client.get(f'course/{course2.id}')
        assert unregistered_response.status_code == 403

        fail_response = client.get('course/123456')
        assert fail_response.status_code == 404

        conftest.create_usercourse(student_user, course2)
        client.get(f'course/{course2.id}')
        template, _ = captured_templates[-1]
        assert template.name == 'exercises.html'
        assert len(list(Exercise.get_objects(student_user.id))) == 2

    @staticmethod
    def test_get_basic_exercises_view():
        basic_view = exercises.get_basic_exercises_view
        assert len(basic_view(course_id=None)) == 0

        course1 = conftest.create_course(index=1)
        course2 = conftest.create_course(index=2)
        assert len(basic_view(course_id=None)) == 0

        ex = [conftest.create_exercise(course1, i) for i in range(3)]
        assert len(basic_view(course_id=None)) == 3
        assert len(basic_view(course_id=course1.id)) == 3
        assert len(basic_view(course_id=course2.id)) == 0
        assert basic_view(course_id=None)[0].id == ex[0].id

        ex2 = [conftest.create_exercise(course2, i) for i in range(3, 6)]
        assert len(basic_view(course_id=None)) == 6
        assert len(basic_view(course_id=course1.id)) == 3
        assert len(basic_view(course_id=course2.id)) == 3
        assert basic_view(course_id=2)[0].id == ex2[0].id
