import time
from unittest.mock import Mock, patch

from flask.testing import FlaskClient

from lms.lmsweb.config import CONFIRMATION_TIME
from lms.lmsdb.models import Course, User
from lms.models.users import generate_user_token
from tests import conftest


class TestRegistration:
    @staticmethod
    def test_invalid_username(
        client: FlaskClient, student_user: User, captured_templates,
    ):
        conftest.signup_client_user(
            client, 'some_name@mail.com', student_user.username,
            'some_name', 'some_password', 'some_password',
        )
        template, _ = captured_templates[-1]
        assert template.name == 'signup.html'

        conftest.login_client_user(
            client, student_user.username, 'some_password',
        )
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

    @staticmethod
    def test_invalid_email(
        client: FlaskClient, student_user: User, captured_templates,
    ):
        conftest.signup_client_user(
            client, student_user.mail_address, 'some_user',
            'some_name', 'some_password', 'some_password',
        )
        client.post('/signup', data={
            'email': student_user.mail_address,
            'username': 'some_user',
            'fullname': 'some_name',
            'password': 'some_password',
            'confirm': 'some_password',
        }, follow_redirects=True)
        template, _ = captured_templates[-1]
        assert template.name == 'signup.html'

        conftest.login_client_user(client, 'some_user', 'some_password')
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

    @staticmethod
    def test_bad_token_or_id(client: FlaskClient):
        conftest.signup_client_user(
            client, 'some_user123@mail.com', 'some_user',
            'some_name', 'some_password', 'some_password',
        )
        user = User.get_or_none(User.username == 'some_user')
        bad_token = 'fake-token43@$@'  # noqa: S105
        fail_confirm_response = client.get(
            f'/confirm-email/{user.id}/{bad_token}', follow_redirects=True,
        )
        assert fail_confirm_response.status_code == 404

        # No such 999 user id
        another_fail_response = client.get(
            f'/confirm-email/999/{bad_token}', follow_redirects=True,
        )
        assert another_fail_response.status_code == 404

    @staticmethod
    def test_use_token_twice(client: FlaskClient):
        conftest.signup_client_user(
            client, 'some_user123@mail.com', 'some_user',
            'some_name', 'some_password', 'some_password',
        )
        user = User.get_or_none(User.username == 'some_user')
        token = generate_user_token(user)
        success_token_response = client.get(
            f'/confirm-email/{user.id}/{token}', follow_redirects=True,
        )
        assert success_token_response.status_code == 200

        fail_token_response = client.get(
            f'/confirm-email/{user.id}/{token}', follow_redirects=True,
        )
        assert fail_token_response.status_code == 403

    @staticmethod
    def test_expired_token(client: FlaskClient):
        conftest.signup_client_user(
            client, 'some_user123@mail.com', 'some_user',
            'some_name', 'some_password', 'some_password',
        )
        user = User.get_or_none(User.username == 'some_user')
        token = generate_user_token(user)

        fake_time = time.time() + CONFIRMATION_TIME + 1
        with patch('time.time', Mock(return_value=fake_time)):
            client.get(
                f'/confirm-email/{user.id}/{token}', follow_redirects=True,
            )
            conftest.login_client_user(client, 'some_user', 'some_password')
            fail_login_response = client.get('/exercises')
            assert fail_login_response.status_code == 302

            token = generate_user_token(user)
            client.get(
                f'/confirm-email/{user.id}/{token}', follow_redirects=True,
            )
            conftest.login_client_user(client, 'some_user', 'some_password')
            success_login_response = client.get('/exercises')
            assert success_login_response.status_code == 200

    @staticmethod
    def test_successful_registration(client: FlaskClient, captured_templates):
        conftest.signup_client_user(
            client, 'some_user123@mail.com', 'some_user',
            'some_name', 'some_password', 'some_password',
        )
        template, _ = captured_templates[-1]
        assert template.name == 'login.html'

        conftest.login_client_user(client, 'some_user', 'some_password')
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

        user = User.get_or_none(User.username == 'some_user')
        token = generate_user_token(user)
        client.get(f'/confirm-email/{user.id}/{token}', follow_redirects=True)
        conftest.login_client_user(client, 'some_user', 'some_password')
        success_login_response = client.get('/exercises')
        assert success_login_response.status_code == 200

    @staticmethod
    def test_registartion_closed(client: FlaskClient, captured_templates):
        conftest.disable_registration()
        conftest.signup_client_user(
            client, 'some_user123@mail.com', 'some_user',
            'some_name', 'some_password', 'some_password',
        )
        user = User.get_or_none(User.username == 'some_user')
        assert user is None

        response = client.get('/signup')
        template, _ = captured_templates[-1]
        assert template.name == 'login.html'
        assert '/signup' not in response.get_data(as_text=True)

    @staticmethod
    def test_register_public_course(
        student_user: User, course: Course, captured_templates,
    ):
        client = conftest.get_logged_user(username=student_user.username)
        not_public_course_response = client.get(f'/course/join/{course.id}')
        assert not_public_course_response.status_code == 403

        unknown_course_response = client.get('/course/join/123456')
        assert unknown_course_response.status_code == 404

        course.is_public = True
        course.save()
        course = Course.get_by_id(course.id)
        client.get(f'/course/join/{course.id}')
        template, _ = captured_templates[-1]
        assert template.name == 'exercises.html'

        already_registered_response = client.get(f'/course/join/{course.id}')
        assert already_registered_response.status_code == 409
