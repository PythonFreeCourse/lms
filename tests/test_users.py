from lms.lmsdb.models import User
from lms.lmsweb import webapp
from tests import conftest


class TestUser:
    def test_password_hashed_on_create(
        self,
        staff_user: User,
        staff_password: str,
    ):
        self.assert_password(staff_user, staff_password)

    def test_password_hashed_on_save(self, staff_user: User):
        new_password = 'woop'  # noqa S105
        staff_user.password = new_password
        staff_user.save()
        self.assert_password(staff_user, new_password)

    def test_password_hashed_on_multiple_saves(self, staff_user: User):
        new_password = 'woop2'  # noqa S105
        staff_user.password = new_password
        staff_user.save()
        staff_user.save()
        self.assert_password(staff_user, new_password)
        staff_user.save()
        self.assert_password(staff_user, new_password)

    @staticmethod
    def assert_password(user: User, password: str):
        assert user.password != password
        assert password not in user.password
        assert user.is_password_valid(password)

    @staticmethod
    def test_view_user_page(
        student_user: User,
        staff_user: User,
    ):
        student_user2 = conftest.create_student_user(index=1)

        client = conftest.get_logged_user(student_user.username)
        user_response = client.get(f'/user/{student_user.id}')
        assert user_response.status_code == 200

        another_user_response = client.get(f'/user/{student_user2.id}')
        assert another_user_response.status_code == 403

        conftest.logout_user(client)
        client2 = conftest.get_logged_user(staff_user.username)
        not_exist_user_response = client2.get('/user/99')
        assert not_exist_user_response.status_code == 404

        another_user_response = client2.get(f'/user/{student_user2.id}')
        assert another_user_response.status_code == 200

    @staticmethod
    def test_logout(student_user: User):
        client = conftest.get_logged_user(student_user.username)
        logout_response = client.get('/logout', follow_redirects=True)
        assert logout_response.status_code == 200

    @staticmethod
    def test_banned_user(banned_user: User):
        client = client = webapp.test_client()
        login_response = client.post('/login', data={
            'username': banned_user.username,
            'password': 'fake pass',
        }, follow_redirects=True)
        assert 'banned' in login_response.get_data(as_text=True)
