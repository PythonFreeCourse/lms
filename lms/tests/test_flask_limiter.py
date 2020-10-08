from lms.tests import conftest
from lms.lmsdb.models import User
from lms.lmsweb import webapp


class TestLimiter:
    @staticmethod
    def test_limiter_login_fails(student_user: User):
        conftest.enable_limiter()
        client = webapp.test_client()
        for _ in range(webapp.config['LIMITS_PER_MINUTE'] - 1):
            response = client.post('/login', data={
                'username': student_user.username,
                'password': 'fake',
            }, follow_redirects=True)
            assert response.status_code == 200

        client = webapp.test_client()
        response = client.post('/login', data={
            'username': student_user.username,
            'password': 'fake5',
        }, follow_redirects=True)
        assert response.status_code == 429

        conftest.disable_limiter()

    @staticmethod
    def test_limiter_login_refreshes():
        conftest.enable_limiter()
        client = webapp.test_client()
        for _ in range(webapp.config['LIMITS_PER_MINUTE'] + 1):
            response = client.get('/login')
            assert response.status_code == 200
        conftest.disable_limiter()

    @staticmethod
    def test_limiter_login_success(student_user: User):
        conftest.enable_limiter()
        client = webapp.test_client()
        client.post('/login', data={
            'username': student_user.username,
            'password': 'fake5',
        }, follow_redirects=True)
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

        client = conftest.get_logged_user(student_user.username)
        success_login_response = client.get('/exercises')
        assert success_login_response.status_code == 200
        conftest.disable_limiter()
