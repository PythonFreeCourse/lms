from lms.lmsdb.models import User
from lms.lmsweb import webapp


class TestLogin:
    @staticmethod
    def test_login_password_fail(student_user: User):
        client = webapp.test_client()
        client.post('/login', data={
            'username': student_user.username,
            'password': 'wrong_pass',
        }, follow_redirects=True)
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

    @staticmethod
    def test_login_username_fail(student_user: User):
        client = webapp.test_client()
        client.post('/login', data={
            'username': 'wrong_user',
            'password': 'fake pass',
        }, follow_redirects=True)
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

    @staticmethod
    def test_login_success(student_user: User):
        client = webapp.test_client()
        client.post('/login', data={
            'username': student_user.username,
            'password': 'fake pass',
        }, follow_redirects=True)
        success_login_response = client.get('/exercises')
        assert success_login_response.status_code == 200
