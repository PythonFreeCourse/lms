from lms.lmsweb.tools.registration import generate_confirmation_token
from lms.lmsdb.models import User
from lms.lmsweb import webapp


class TestRegistration:
    @staticmethod
    def test_invalid_username(student_user: User):
        client = webapp.test_client()
        response = client.post('/signup', data={
            'email': 'some_name@mail.com',
            'username': student_user.username,
            'fullname': 'some_name',
            'password': 'some_password',
            'confirm': 'some_password',
        }, follow_redirects=True)
        assert response.request.path == '/signup'

        client.post('/login', data={
            'username': student_user.username,
            'password': 'some_password',
        }, follow_redirects=True)
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

    @staticmethod
    def test_invalid_email(student_user: User):
        client = webapp.test_client()
        response = client.post('/signup', data={
            'email': student_user.mail_address,
            'username': 'some_user',
            'fullname': 'some_name',
            'password': 'some_password',
            'confirm': 'some_password',
        }, follow_redirects=True)
        assert response.request.path == '/signup'

        client.post('/login', data={
            'username': 'some_user',
            'password': 'some_password',
        }, follow_redirects=True)
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

    @staticmethod
    def test_successful_registration():
        client = webapp.test_client()
        response = client.post('/signup', data={
            'email': 'some_user123@mail.com',
            'username': 'some_user',
            'fullname': 'some_name',
            'password': 'some_password',
            'confirm': 'some_password',
        }, follow_redirects=True)
        assert response.request.path == '/login'

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
