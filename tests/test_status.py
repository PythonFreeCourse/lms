from lms.lmsdb.models import Solution
from tests import conftest


class TestStatusPage:
    @classmethod
    def setup(cls):
        cls.course1 = conftest.create_course(1)
        cls.course2 = conftest.create_course(2)
        cls.course_no_submissions = conftest.create_course(3)
        cls.course_no_exercises = conftest.create_course(4)

        cls.ex1_1 = conftest.create_exercise(cls.course1, 1, 1)
        cls.ex1_2 = conftest.create_exercise(cls.course1, 2, 2)
        cls.ex2_1 = conftest.create_exercise(cls.course2, 1, 3)
        cls.ex3_1 = conftest.create_exercise(cls.course_no_submissions, 1, 4)

        cls.user1 = conftest.create_user(index=1)
        cls.user2 = conftest.create_user(index=2)

        conftest.create_usercourse(cls.user1, cls.course1)
        conftest.create_usercourse(cls.user1, cls.course2)
        conftest.create_usercourse(cls.user2, cls.course1)

        solution = conftest.create_solution

        cls.s1 = solution(cls.ex1_1, cls.user1)
        cls.s2 = solution(cls.ex1_1, cls.user1, code='Other submission')
        cls.s3 = solution(cls.ex1_1, cls.user2)
        cls.s4 = solution(cls.ex1_2, cls.user1)

        cls.s5 = solution(cls.ex2_1, cls.user1)

    def test_simple_course(self):
        course_1 = list(Solution.status(course_id=self.course1.id).dicts())
        course_2 = list(Solution.status(course_id=self.course2.id).dicts())
        assert len(course_1) == 2
        assert len(course_2) == 1

        ex1_1 = next(filter(lambda e: e['id'] == self.ex1_1.id, course_1))
        ex1_2 = next(filter(lambda e: e['id'] == self.ex1_2.id, course_1))
        ex2_1 = next(filter(lambda e: e['id'] == self.ex2_1.id, course_2))
        assert ex1_1['submitted'] == 2
        assert ex1_2['submitted'] == 1
        assert ex2_1['submitted'] == 1

    def test_all_together(self):
        all_courses = list(Solution.status().dicts())
        assert len(all_courses) == 3

        ex1_1 = next(filter(lambda e: e['id'] == self.ex1_1.id, all_courses))
        ex1_2 = next(filter(lambda e: e['id'] == self.ex1_2.id, all_courses))
        ex2_1 = next(filter(lambda e: e['id'] == self.ex2_1.id, all_courses))
        assert ex1_1['submitted'] == 2
        assert ex1_2['submitted'] == 1
        assert ex2_1['submitted'] == 1

    def test_no_submissions(self):
        submissions = list(Solution.status(self.course_no_submissions).dicts())
        assert not submissions

    def test_no_exercises(self):
        submissions = list(Solution.status(self.course_no_exercises).dicts())
        assert not submissions
