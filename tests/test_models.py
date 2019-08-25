from lmsweb.models import Course, User


class TestCourse:
    def test_add_user(self, user: User, course: Course):
        course.add_user(user)
        assert user.course == course

    def test_remove_user(self, user: User, course: Course):
        course.add_user(user)

        assert user.course == course
        course.remove_user(user)
        assert user.course is None

    def test_administrators(self, admin_user: User, course: Course):
        assert course.administrators.count() == 0
        course.add_user(admin_user)
        assert admin_user.course.administrators.count() == 1
        assert admin_user.course.administrators[0] == admin_user
