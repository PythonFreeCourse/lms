from flask.testing import FlaskClient

from lms.lmsdb.models import User


class TestLogin:
    @staticmethod
    def test_login_password_fail(client: FlaskClient, student_user: User):
        client.post('/login', data={
            'username': student_user.username,
            'password': 'wrong_pass',
        }, follow_redirects=True)
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

    @staticmethod
    def test_login_username_fail(client: FlaskClient):
        client.post('/login', data={
            'username': 'wrong_user',
            'password': 'fake pass',
        }, follow_redirects=True)
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

    @staticmethod
    def test_login_unverified_user(
        client: FlaskClient, unverified_user: User, captured_templates,
    ):
        client.post('/login', data={
            'username': unverified_user.username,
            'password': 'fake pass',
        }, follow_redirects=True)
        template, _ = captured_templates[-1]
        assert template.name == 'login.html'

        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

    @staticmethod
    def test_login_success(client: FlaskClient, student_user: User):
        client.post('/login', data={
            'username': student_user.username,
            'password': 'fake pass',
        }, follow_redirects=True)
        success_login_response = client.get('/exercises')
        assert success_login_response.status_code == 200
