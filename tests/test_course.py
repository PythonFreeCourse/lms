from lms.lmsdb.models import Course
from lms.models import courses
from tests import conftest


class TestCourse:
    @staticmethod
    def test_course_exercises(course: Course):
        ex1 = conftest.create_exercise(course, 0)
        ex2 = conftest.create_exercise(course, 1)
        exercises = course.get_exercise_ids()
        assert len(exercises) == 2
        assert ex1.id in exercises
        assert ex2.id in exercises

    @staticmethod
    def test_course_name():
        course = conftest.create_course(name='Test course')
        assert course.name == 'Test course'

    @staticmethod
    def test_course_students(course: Course):
        course_id = course.id
        students = [conftest.create_user(index=i) for i in range(3)]

        # No users in course
        assert len(courses.get_students(course_id)) == 0

        # Add users to course
        for student in students:
            conftest.create_usercourse(student, course)

        discovered = courses.get_students(course_id)
        assert len(discovered) == 3
