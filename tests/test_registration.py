from flask.testing import FlaskClient

from lms.lmsweb.tools.registration import generate_confirmation_token
from lms.lmsdb.models import User


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

        token = generate_confirmation_token('some_user123@mail.com')
        client.get(f'/confirm-email/{token}', follow_redirects=True)
        client.post('/login', data={
            'username': 'some_user',
            'password': 'some_password',
        }, follow_redirects=True)
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 200
