import datetime

from lms.lmsdb.models import Course, Exercise, Solution, User
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

    @staticmethod
    def test_course_objects_structure(course: Course, student_user: User):
        # Create more courses
        course2 = conftest.create_course(index=1)
        course3 = conftest.create_course(index=2)

        # Create another student user
        student_user2 = conftest.create_student_user(index=1)

        # Assign users to courses
        conftest.create_usercourse(student_user, course)
        conftest.create_usercourse(student_user, course3)
        conftest.create_usercourse(student_user2, course2)

        # Create exercises for the courses
        conftest.create_exercise(course, 1)
        ex2_c1 = conftest.create_exercise(course, 2)
        ex1_c2 = conftest.create_exercise(course2, 1)
        conftest.create_exercise(course2, 2)
        conftest.create_exercise(course3, 1)

        # Create solutions
        conftest.create_solution(ex2_c1, student_user)
        conftest.create_solution(ex1_c2, student_user2)

        # Dicts of dicts structures
        user_structure1 = Solution.of_user(student_user)
        user_structure2 = Solution.of_user(student_user2)

        assert len(user_structure1) == 2
        assert len(user_structure2) == 1
        assert 'solution_id' in user_structure1.get('course 0').get(2)
        assert len(user_structure1.get('course 0')) == 2
        assert len(user_structure1.get('course 2')) == 1
        assert len(user_structure2.get('course 1')) == 2
        assert (
            user_structure2.get('course 1').get(4).get('exercise_number') == 2,
        )
        assert 'solution_id' in user_structure2.get('course 1').get(3)
