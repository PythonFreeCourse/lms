import http
from unittest import mock

from flask.testing import FlaskClient

from lms.lmsdb.models import Solution
from lms.lmsweb import routes
from tests import conftest


celery_async = (
    "lms.lmstests.public.general.tasks."
    "reset_solution_state_if_needed.apply_async"
)
no_celery = mock.patch(celery_async, lambda *args, **kwargs: None)


class TestCheckPages:
    @classmethod
    def setup_method(cls):
        cls.course = conftest.create_course()
        cls.user = conftest.create_user(index=1)
        cls.user2 = conftest.create_user(index=2)
        cls.exercise = conftest.create_exercise(cls.course, number=1)

        solution = conftest.create_solution
        cls.solution1 = solution(cls.exercise, cls.user, code="A")
        cls.solution2 = solution(cls.exercise, cls.user, code="B")
        cls.solution3 = solution(cls.exercise, cls.user2)

    @classmethod
    def test_start_checking(cls, admin_client: FlaskClient):
        check_url = f"check/exercise/{cls.exercise.id}"

        with no_celery:
            # You should check the newer, not the older (same user)
            response = admin_client.get(check_url, follow_redirects=True)
            assert response.request.url.endswith(f"view/{cls.solution2.id}")

            # First exercise should be marked as checking
            response = admin_client.get(check_url, follow_redirects=True)
            assert response.request.url.endswith(f"view/{cls.solution3.id}")

            # All exercises are checked
            response = admin_client.get(check_url, follow_redirects=True)
            status_page = response.request.url.strip("/")
            assert status_page.endswith(f"/{routes.STATUS.strip('/')}")

    @classmethod
    def test_check_solution(cls, admin_client: FlaskClient):
        check_url = "check/solution/{}"
        go_to = admin_client.get
        solution = check_url.format

        with no_celery:
            response = go_to(solution(5000), follow_redirects=True)
            assert response.status_code == http.HTTPStatus.NOT_FOUND

            assert cls.solution1.state == Solution.STATES.CREATED.name
            response = go_to(solution(cls.solution1.id), follow_redirects=True)
            assert response.request.url.endswith(f"view/{cls.solution1.id}")
            cls.solution1 = Solution.get_by_id(cls.solution1.id)  # Must refresh
            assert cls.solution1.state == Solution.STATES.IN_CHECKING.name

            cls.solution1.mark_as_checked()
            response = go_to(solution(cls.solution1.id), follow_redirects=True)
            assert response.request.url.endswith(f"view/{cls.solution1.id}")
