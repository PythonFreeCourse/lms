import datetime

from lms.lmsdb.models import Course, Exercise, User
from lms.models import tags
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
    def test_exercise_tags(
        student_user: User, course: Course, exercise: Exercise,
    ):
        client = conftest.get_logged_user(username=student_user.username)
        conftest.create_usercourse(student_user, course)
        client.get(f'course/{course.id}')
        conftest.create_exercise_tag('tag1', course, exercise)
        tag_response = client.get('/exercises/tag1')
        assert tag_response.status_code == 200

        course2 = conftest.create_course(index=1)
        exercise2 = conftest.create_exercise(course2, 2)
        conftest.create_usercourse(student_user, course2)
        conftest.create_exercise_tag('tag2', course2, exercise2)
        bad_tag_response = client.get('/exercises/tag2')
        assert bad_tag_response.status_code == 404

        client.get(f'course/{course2.id}')
        success_tag_response = client.get('/exercises/tag2')
        assert success_tag_response.status_code == 200

        another_bad_tag_response = client.get('/exercises/wrongtag')
        assert another_bad_tag_response.status_code == 404

    @staticmethod
    def test_course_tags(course: Course, exercise: Exercise):
        course2 = conftest.create_course(index=1)
        conftest.create_exercise_tag('tag1', course, exercise)
        conftest.create_exercise_tag('tag2', course, exercise)
        exercise2 = conftest.create_exercise(course, 2)
        conftest.create_exercise_tag('tag1', course, exercise2)
        assert len(tags.by_course(course=course.id)) == 3
        assert len(
            tags.by_exercise_number(course=course.id, number=exercise.number),
        ) == 2
        assert len(tags.by_exercise_id(exercise_id=exercise2.id)) == 1
        assert len(tags.by_course(course=course2.id)) == 0
