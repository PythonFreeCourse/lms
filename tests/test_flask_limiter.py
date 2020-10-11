from lms.lmsdb.models import User
from lms.lmsweb import webapp
from tests import conftest


class TestLimiter:
    @staticmethod
    @conftest.use_limiter
    def test_limiter_login_fails(student_user: User):
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

    @staticmethod
    @conftest.use_limiter
    def test_limiter_login_refreshes():
        client = webapp.test_client()
        for _ in range(webapp.config['LIMITS_PER_MINUTE'] + 1):
            response = client.get('/login')
            assert response.status_code == 200

    @staticmethod
    @conftest.use_limiter
    def test_limiter_login_success(student_user: User):
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
