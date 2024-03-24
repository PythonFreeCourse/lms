from tests import conftest


class TestSubmissionsPage:
    @classmethod
    def setup_method(cls):
        # Setup users
        cls.user1 = conftest.create_user(index=1)
        cls.user2 = conftest.create_user(index=2)
        cls.user3 = conftest.create_user(index=3)
        cls.user_ids = [1, 2, 3]

        # Setup courses
        cls.course1 = conftest.create_course(1)
        cls.course2 = conftest.create_course(2)
        cls.course3 = conftest.create_course(3)

        # Setup exercises
        cls.ex1_1 = conftest.create_exercise(cls.course1, 1, 1)
        cls.ex1_2 = conftest.create_exercise(cls.course1, 2, 2)
        cls.ex1_3 = conftest.create_exercise(cls.course1, 3, 3)
        cls.ex1_4 = conftest.create_exercise(cls.course1, 4, 4)
        cls.exercise_ids = [1, 2, 3, 4]

        cls.ex2_1 = conftest.create_exercise(cls.course2, 1, 5)
        cls.ex2_2 = conftest.create_exercise(cls.course2, 2, 6)
        cls.ex2_3 = conftest.create_exercise(cls.course2, 3, 7)
        cls.ex2_4 = conftest.create_exercise(cls.course2, 4, 8)

        # Connect users to courses
        conftest.create_usercourse(cls.user1, cls.course1)
        conftest.create_usercourse(cls.user2, cls.course1)
        conftest.create_usercourse(cls.user3, cls.course1)

        conftest.create_usercourse(cls.user1, cls.course3)
        conftest.create_usercourse(cls.user2, cls.course3)

        # Create solutions
        solution = conftest.create_solution
        cls.s1 = solution(cls.ex1_1, cls.user1)
        cls.s2 = solution(cls.ex1_1, cls.user1, code='Other submission')
        cls.s3 = solution(cls.ex1_1, cls.user2)
        cls.s4 = solution(cls.ex1_2, cls.user1)
        cls.s5 = solution(cls.ex2_1, cls.user1)

    @classmethod
    def test_we_get_users_x_exercises_results(cls, db):
        all_solutions = cls.course1.get_matrix(db)
        solution_count = len(cls.user_ids) * len(cls.exercise_ids)
        assert len(all_solutions) == solution_count

        assert len(cls.course2.get_matrix(db)) == 0

        students_count = len(cls.course3.get_students())
        exercise_count = len(cls.course3.get_exercise_ids())
        solution_count = students_count * exercise_count
        assert len(cls.course3.get_matrix(db)) == solution_count
