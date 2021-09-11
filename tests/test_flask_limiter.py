from flask.testing import FlaskClient

from lms.lmsweb import routes
from lms.lmsdb.models import Solution, User
from lms.lmsweb import webapp
from tests import conftest


class TestLimiter:
    @staticmethod
    @conftest.use_limiter
    def test_limiter_login_fails(client: FlaskClient, student_user: User):
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
    def test_limiter_login_refreshes(client: FlaskClient):
        for _ in range(webapp.config['LIMITS_PER_MINUTE'] + 1):
            response = client.get('/login')
            assert response.status_code == 200

    @staticmethod
    @conftest.use_limiter
    def test_limiter_login_success(client: FlaskClient, student_user: User):
        client.post('/login', data={
            'username': student_user.username,
            'password': 'fake5',
        }, follow_redirects=True)
        fail_login_response = client.get('/exercises')
        assert fail_login_response.status_code == 302

        client = conftest.get_logged_user(student_user.username)
        success_login_response = client.get('/exercises')
        assert success_login_response.status_code == 200

    @staticmethod
    @conftest.use_limiter
    def test_limiter_shared_link(student_user: User, solution: Solution):
        client = conftest.get_logged_user(student_user.username)
        shared_solution = conftest.create_shared_solution(solution)
        for _ in range(webapp.config['LIMITS_PER_MINUTE']):
            response = client.get(f'{routes.SHARED}/{shared_solution}')
            assert response.status_code == 200
        response = client.get(f'{routes.SHARED}/{shared_solution}')
        assert response.status_code == 429
