from flask.testing import FlaskClient

from lms.lmsdb.models import User
from tests import conftest


class TestLogin:
    @staticmethod
    def test_login_password_fail(client: FlaskClient, student_user: User):
        conftest.login_client_user(client, student_user.username, 'wrong_pass')
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

    @staticmethod
    def test_login_username_fail(client: FlaskClient):
        conftest.login_client_user(client, 'wrong user', 'fake pass')
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

    @staticmethod
    def test_login_unverified_user(
        client: FlaskClient, unverified_user: User, captured_templates,
    ):
        conftest.login_client_user(
            client, unverified_user.username, 'fake pass',
        )
        template, _ = captured_templates[-1]
        assert template.name == 'login.html'

        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

    @staticmethod
    def test_login_success(client: FlaskClient, student_user: User):
        conftest.login_client_user(client, student_user.username, 'fake pass')
        success_login_response = client.get('/exercises')
        assert success_login_response.status_code == 200
