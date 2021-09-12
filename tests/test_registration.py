import time
from unittest.mock import Mock, patch

from flask.testing import FlaskClient

from lms.lmsweb.config import CONFIRMATION_TIME
from lms.lmsdb.models import User
from lms.models.register import generate_confirmation_token
from tests import conftest


class TestRegistration:
    @staticmethod
    def test_invalid_username(
        client: FlaskClient, student_user: User, captured_templates,
    ):
        client.post('/signup', data={
            'email': 'some_name@mail.com',
            'username': student_user.username,
            'fullname': 'some_name',
            'password': 'some_password',
            'confirm': 'some_password',
        }, follow_redirects=True)
        template, _ = captured_templates[-1]
        assert template.name == "signup.html"

        client.post('/login', data={
            'username': student_user.username,
            'password': 'some_password',
        }, follow_redirects=True)
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

    @staticmethod
    def test_invalid_email(
        client: FlaskClient, student_user: User, captured_templates,
    ):
        client.post('/signup', data={
            'email': student_user.mail_address,
            'username': 'some_user',
            'fullname': 'some_name',
            'password': 'some_password',
            'confirm': 'some_password',
        }, follow_redirects=True)
        template, _ = captured_templates[-1]
        assert template.name == 'signup.html'

        client.post('/login', data={
            'username': 'some_user',
            'password': 'some_password',
        }, follow_redirects=True)
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

    @staticmethod
    def test_successful_registration(client: FlaskClient, captured_templates):
        client.post('/signup', data={
            'email': 'some_user123@mail.com',
            'username': 'some_user',
            'fullname': 'some_name',
            'password': 'some_password',
            'confirm': 'some_password',
        }, follow_redirects=True)
        template, _ = captured_templates[-1]
        assert template.name == 'login.html'

        client.post('/login', data={
            'username': 'some_user',
            'password': 'some_password',
        }, follow_redirects=True)
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

        user = User.get_or_none(User.username == 'some_user')
        token = generate_confirmation_token(user)
        client.get(f'/confirm-email/{user.id}/{token}', follow_redirects=True)
        client.post('/login', data={
            'username': 'some_user',
            'password': 'some_password',
        }, follow_redirects=True)
        success_login_response = client.get('/exercises')
        assert success_login_response.status_code == 200

    @staticmethod
    def test_bad_token_or_id(client: FlaskClient):
        client.post('/signup', data={
            'email': 'some_user123@mail.com',
            'username': 'some_user',
            'fullname': 'some_name',
            'password': 'some_password',
            'confirm': 'some_password',
        }, follow_redirects=True)
        user = User.get_or_none(User.username == 'some_user')
        bad_token = "fake-token43@$@"
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
        client.post('/signup', data={
            'email': 'some_user123@mail.com',
            'username': 'some_user',
            'fullname': 'some_name',
            'password': 'some_password',
            'confirm': 'some_password',
        }, follow_redirects=True)
        user = User.get_or_none(User.username == 'some_user')
        token = generate_confirmation_token(user)
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
        client.post('/signup', data={
            'email': 'some_user123@mail.com',
            'username': 'some_user',
            'fullname': 'some_name',
            'password': 'some_password',
            'confirm': 'some_password',
        }, follow_redirects=True)
        user = User.get_or_none(User.username == 'some_user')
        token = generate_confirmation_token(user)

        fake_time = time.time() + CONFIRMATION_TIME + 1
        with patch('time.time', Mock(return_value=fake_time)):
            client.get(
                f'/confirm-email/{user.id}/{token}', follow_redirects=True,
            )
            client.post('/login', data={
                'username': 'some_user',
                'password': 'some_password',
            }, follow_redirects=True)
            fail_login_response = client.get('/exercises')
            assert fail_login_response.status_code == 302

            token = generate_confirmation_token(user)
            client.get(
                f'/confirm-email/{user.id}/{token}', follow_redirects=True,
            )
            client.post('/login', data={
                'username': 'some_user',
                'password': 'some_password',
            }, follow_redirects=True)
            success_login_response = client.get('/exercises')
            assert success_login_response.status_code == 200

    @staticmethod
    def test_registartion_closed(client: FlaskClient, captured_templates):
        conftest.disable_registration()
        client.post('/signup', data={
            'email': 'some_user123@mail.com',
            'username': 'some_user',
            'fullname': 'some_name',
            'password': 'some_password',
            'confirm': 'some_password',
        }, follow_redirects=True)
        user = User.get_or_none(User.username == 'some_user')
        assert user is None

        response = client.get('/signup')
        template, _ = captured_templates[-1]
        assert template.name == 'login.html'
        assert '/signup' not in response.get_data(as_text=True)
