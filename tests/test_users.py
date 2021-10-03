import time
from unittest.mock import Mock, patch

from flask.testing import FlaskClient

from lms.lmsdb.models import Course, User
from lms.lmsweb.config import CONFIRMATION_TIME, MAX_INVALID_PASSWORD_TRIES
from lms.models.users import generate_user_token
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
    def test_banned_user(client: FlaskClient, banned_user: User):
        login_response = conftest.login_client_user(
            client, banned_user.username, 'fake pass',
        )
        assert 'banned' in login_response.get_data(as_text=True)

    @staticmethod
    def test_invalid_change_password(captured_templates):
        student_user = conftest.create_student_user(index=1)
        client = conftest.get_logged_user(student_user.username)
        for _ in range(MAX_INVALID_PASSWORD_TRIES):
            conftest.change_client_password(
                client, 'wrong pass', 'some_password', 'some_password',
            )
            template, _ = captured_templates[-1]
            assert template.name == "change-password.html"

        conftest.change_client_password(
            client, 'fake pass', 'some_password', 'some_password',
        )
        template, _ = captured_templates[-1]
        assert template.name == "change-password.html"

    @staticmethod
    def test_valid_change_password(captured_templates):
        student_user = conftest.create_student_user(index=1)
        client = conftest.get_logged_user(student_user.username)
        conftest.change_client_password(
            client, 'fake pass', 'some_password', 'some_password',
        )
        template, _ = captured_templates[-1]
        assert template.name == "login.html"
        check_logout_response = client.get('/exercises')
        assert check_logout_response.status_code == 302

    @staticmethod
    def test_forgot_my_password_invalid_mail(
        client: FlaskClient, captured_templates,
    ):
        conftest.reset_client_password(client, 'fake-mail@mail.com')
        template, _ = captured_templates[-1]
        assert template.name == "reset-password.html"

    @staticmethod
    def test_forgot_my_password_invalid_recover(
        client: FlaskClient, captured_templates,
    ):
        user = conftest.create_student_user(index=1)
        conftest.reset_client_password(client, user.mail_address)
        template, _ = captured_templates[-1]
        assert template.name == "login.html"

        token = generate_user_token(user)
        unknown_id_recover_response = conftest.recover_client_password(
            client, user.id + 1, token, 'different pass', 'different pass',
        )
        assert unknown_id_recover_response.status_code == 404

        conftest.recover_client_password(
            client, user.id, token, 'wrong pass', 'different pass',
        )
        template, _ = captured_templates[-1]
        assert template.name == "recover-password.html"

    @staticmethod
    def test_forgot_my_password(client: FlaskClient, captured_templates):
        user = conftest.create_student_user(index=1)
        conftest.reset_client_password(client, user.mail_address)
        template, _ = captured_templates[-1]
        assert template.name == "login.html"

        token = generate_user_token(user)
        conftest.recover_client_password(
            client, user.id, token, 'new pass', 'new pass',
        )
        template, _ = captured_templates[-1]
        assert template.name == "login.html"

        second_try_response = conftest.recover_client_password(
            client, user.id, token, 'new pass1', 'new pass1',
        )
        assert second_try_response.status_code == 404

        conftest.login_client_user(client, user.username, 'fake pass')
        template, _ = captured_templates[-1]
        assert template.name == 'login.html'

        conftest.login_client_user(client, user.username, 'new pass')
        template, _ = captured_templates[-1]
        assert template.name == 'exercises.html'

    @staticmethod
    def test_expired_token(client: FlaskClient):
        user = conftest.create_student_user(index=1)
        conftest.reset_client_password(client, user.mail_address)
        token = generate_user_token(user)

        fake_time = time.time() + CONFIRMATION_TIME + 1
        with patch('time.time', Mock(return_value=fake_time)):
            conftest.recover_client_password(
                client, user.id, token, 'new pass1', 'new pass1',
            )
            conftest.login_client_user(client, user.username, 'new pass1')
            fail_login_response = client.get('/exercises')
            assert fail_login_response.status_code == 302

            conftest.login_client_user(client, user.username, 'fake pass')
            fail_login_response = client.get('/exercises')
            assert fail_login_response.status_code == 200

    @staticmethod
    def test_user_registered_to_course(student_user: User, course: Course):
        conftest.create_usercourse(student_user, course)
        assert course.has_user(student_user)

        course2 = conftest.create_course(index=1)
        assert not course2.has_user(student_user)

