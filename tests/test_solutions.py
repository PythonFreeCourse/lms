from lms.models.errors import ResourceNotFound
from lms.models.solutions import get_view_parameters
from unittest import mock

from flask import json
import pytest

from lms.lmsdb.models import Comment, Exercise, SharedSolution, Solution, User
from lms.lmstests.public.general import tasks as general_tasks
from lms.lmsweb import routes
from lms.models import notifications, solutions
from tests import conftest


celery_async = (
    'lms.lmstests.public.general.tasks'
    '.reset_solution_state_if_needed.apply_async'
)
no_celery = mock.patch(celery_async, lambda *args, **kwargs: None)


class TestSolutionDb:
    old_solution_state = Solution.STATES.OLD_SOLUTION.name
    in_checking_state = Solution.STATES.IN_CHECKING.name
    created_state = Solution.STATES.CREATED.name

    def test_new_solution_override_old_solutions(
        self,
        exercise: Exercise,
        student_user: User,
    ):
        first_solution = conftest.create_solution(exercise, student_user)
        second_solution = conftest.create_solution(exercise, student_user)
        assert second_solution.state == self.created_state
        assert first_solution.refresh().state == self.old_solution_state

        next_unchecked = Solution.next_unchecked()
        assert next_unchecked is not None
        assert next_unchecked.id == second_solution.id
        next_unchecked = Solution.next_unchecked_of(exercise.id)
        assert next_unchecked is not None
        assert next_unchecked.id == second_solution.id
        assert next_unchecked.start_checking()
        assert next_unchecked.refresh().state == self.in_checking_state

        assert Solution.next_unchecked() is None
        assert Solution.next_unchecked_of(exercise.id) is None

        general_tasks.reset_solution_state_if_needed(second_solution.id)
        next_unchecked = Solution.next_unchecked()
        next_unchecked_by_id = Solution.next_unchecked_of(exercise.id)
        assert next_unchecked is not None and next_unchecked_by_id is not None
        assert next_unchecked.id == second_solution.id
        assert next_unchecked_by_id.id == second_solution.id

        third_solution = conftest.create_solution(
            exercise, student_user, code='123',
        )
        fourth_solution = conftest.create_solution(
            exercise, student_user, code='1234',
        )
        assert not Solution.is_duplicate(
            third_solution.hashed, student_user, exercise, already_hashed=True,
        )
        assert Solution.is_duplicate(
            fourth_solution.hashed, student_user, exercise,
            already_hashed=True,
        )

    @staticmethod
    def test_next_exercise_with_cleanest_code(
        comment: Comment,
        staff_user: User,
    ):
        student_user: User = conftest.create_student_user(index=1)
        first_solution = comment.solution
        comment_text = comment.comment
        second_solution = conftest.create_solution(
            comment.solution.exercise, student_user)

        # comment exists on first solution - second one should be the first
        next_unchecked = Solution.next_unchecked()
        assert next_unchecked is not None
        assert next_unchecked.id == second_solution.id

        # delete the comment should give us back the first solution
        Comment.delete_by_id(comment.id)
        next_unchecked = Solution.next_unchecked()
        assert next_unchecked is not None
        assert next_unchecked.id == first_solution.id

        # if second_solution has comments we should get first solution
        Comment.create_comment(
            commenter=staff_user,
            line_number=1,
            comment_text=comment_text,
            file=second_solution.solution_files.get(),
            is_auto=False,
        )
        next_unchecked = Solution.next_unchecked()
        assert next_unchecked is not None
        assert next_unchecked.id == first_solution.id

        # both have comments - the first one should be the first solution
        Comment.create_comment(
            commenter=staff_user,
            line_number=1,
            comment_text=comment_text,
            file=first_solution.solution_files.get(),
            is_auto=False,
        )
        next_unchecked = Solution.next_unchecked()
        assert next_unchecked is not None
        assert next_unchecked.id == first_solution.id


class TestSolutionBridge:
    @staticmethod
    def test_mark_as_checked(
        exercise: Exercise,
        student_user: User,
        staff_user: User,
        solution: Solution,
    ):
        # Basic functionality
        assert solution.state == Solution.STATES.CREATED.name
        marked = solutions.mark_as_checked(solution.id, staff_user.id)
        # HELL WITH PEEWEE!!!
        solution = Solution.get_by_id(solution.id)
        assert marked
        assert solution.state == Solution.STATES.DONE.name
        assert solution.checker == staff_user

        # Not duplicating things
        staff_user2 = conftest.create_staff_user(index=1)
        solution2 = conftest.create_solution(exercise, student_user)
        marked = solutions.mark_as_checked(solution2.id, staff_user2.id)
        solution2 = Solution.get_by_id(solution2.id)
        assert solution2.state == Solution.STATES.DONE.name
        assert solution2.checker == staff_user2

        # Creates notifications
        assert len(list(notifications.get(student_user))) == 2

    @staticmethod
    def test_get_next_unchecked(
        student_user: User,
        exercise: Exercise,
        staff_user: User,
    ):
        student_user2 = conftest.create_student_user(index=1)
        exercise2 = conftest.create_exercise(3)
        solution1 = conftest.create_solution(exercise, student_user)
        solution2 = conftest.create_solution(exercise2, student_user)
        solution3 = conftest.create_solution(exercise, student_user2)

        assert len(list(Solution.select())) == 3

        unchecked = solutions.get_next_unchecked(exercise.id)
        assert unchecked is not None
        assert unchecked.exercise.id == solution1.exercise.id
        assert unchecked == solution1

        solutions.mark_as_checked(solution1.id, staff_user)
        unchecked = solutions.get_next_unchecked(exercise.id)
        assert unchecked is not None
        assert unchecked.exercise.id == solution3.exercise.id
        assert unchecked == solution3

        solutions.mark_as_checked(solution3.id, staff_user)
        unchecked = solutions.get_next_unchecked(exercise.id)
        assert unchecked is None

        unchecked = solutions.get_next_unchecked()
        assert unchecked is not None
        assert unchecked == solution2

        solutions.mark_as_checked(solution2.id, staff_user)
        unchecked = solutions.get_next_unchecked()
        assert unchecked is None

        unchecked = solutions.get_next_unchecked(solution2.id)
        assert unchecked is None

    @staticmethod
    def test_start_checking(exercise: Exercise, student_user: User):
        student_user2 = conftest.create_student_user(index=1)
        exercise2 = conftest.create_exercise(1)
        solution1 = conftest.create_solution(exercise, student_user)
        solution2 = conftest.create_solution(exercise2, student_user)
        solution3 = conftest.create_solution(exercise, student_user2)

        is_checking = solutions.start_checking(solution=None)
        assert not is_checking

        with no_celery:
            for solution in (solution1, solution2, solution3):
                assert solution.state == Solution.STATES.CREATED.name
                is_checking = solutions.start_checking(solution=solution)
                assert is_checking
                the_solution = Solution.get_by_id(solution.id)
                assert the_solution.state == Solution.STATES.IN_CHECKING.name

    @staticmethod
    def test_user_comments(
        exercise: Exercise,
        student_user: User,
    ):
        solution = conftest.create_solution(exercise, student_user)

        client = conftest.get_logged_user(student_user.username)
        # Creating a comment
        comment_response = client.post('/comments', data=json.dumps({
            'fileId': solution.files[0].id, 'act': 'create', 'kind': 'text',
            'comment': 'hey', 'line': 1,
        }), content_type='application/json')
        assert comment_response.status_code == 200

        # Creating another comment
        another_comment_response = client.post(
            '/comments', data=json.dumps({
                'fileId': solution.files[0].id, 'act': 'create',
                'kind': 'text', 'comment': 'noice', 'line': 2,
            }), content_type='application/json',
        )
        assert another_comment_response.status_code == 200

        # Removing the second comment
        json_response_another_comment = json.loads(
            another_comment_response.get_data(as_text=True),
        )
        delete_response = client.get('/comments', query_string={
            'fileId': solution.files[0].id, 'act': 'delete',
            'commentId': json_response_another_comment['id'],
        }, content_type='application/json')
        assert delete_response.status_code == 200

        # Disabling users comments option
        conftest.disable_users_comments()

        # Trying to remove a comment
        json_response_comment = json.loads(
            comment_response.get_data(as_text=True),
        )
        delete_response = client.get('/comments', query_string={
            'fileId': solution.files[0].id, 'act': 'delete',
            'commentId': json_response_comment['id'],
        }, content_type='application/json')
        assert delete_response.status_code == 403

        # Trying to create a comment
        disable_comment_response = client.post(
            '/comments', data=json.dumps({
                'fileId': solution.files[0].id, 'act': 'create',
                'kind': 'text', 'comment': 'well well well', 'line': 2,
            }), content_type='application/json',
        )
        assert disable_comment_response.status_code == 403

    @staticmethod
    def test_staff_and_user_comments(
        exercise: Exercise,
        student_user: User,
        staff_user: User,
    ):
        solution = conftest.create_solution(exercise, student_user)

        client = conftest.get_logged_user(staff_user.username)
        # Enabling user comments option
        conftest.enable_users_comments()
        # Creating a comment
        comment_response = client.post('/comments', data=json.dumps({
            'fileId': solution.files[0].id, 'act': 'create', 'kind': 'text',
            'comment': 'try again', 'line': 1,
        }), content_type='application/json')
        assert comment_response.status_code == 200

        # Creating another comment
        another_comment_response = client.post(
            '/comments', data=json.dumps({
                'fileId': solution.files[0].id, 'act': 'create',
                'kind': 'text', 'comment': 'hey', 'line': 1,
            }), content_type='application/json',
        )
        assert another_comment_response.status_code == 200

        # Unknown act comment
        unknown_comment_response = client.post(
            '/comments', data=json.dumps({
                'fileId': solution.files[0].id, 'act': 'unknown',
                'kind': 'text', 'comment': 'hey', 'line': 1,
            }), content_type='application/json',
        )
        assert unknown_comment_response.status_code == 400

        # Not existing fileId comment
        file_id_comment_response = client.post(
            '/comments', data=json.dumps({
                'fileId': 99, 'act': 'create',
                'kind': 'text', 'comment': 'hey', 'line': 1,
            }), content_type='application/json',
        )
        assert file_id_comment_response.status_code == 404

        # Removing the second comment
        json_response_another_comment = json.loads(
            another_comment_response.get_data(as_text=True),
        )
        delete_response = client.get('/comments', query_string={
            'fileId': solution.files[0].id, 'act': 'delete',
            'commentId': json_response_another_comment['id'],
        }, content_type='application/json')
        assert delete_response.status_code == 200

        conftest.logout_user(client)
        client2 = conftest.get_logged_user(student_user.username)
        # Trying to remove a comment
        json_response_comment = json.loads(
            comment_response.get_data(as_text=True),
        )
        delete_response = client2.get('/comments', query_string={
            'fileId': solution.files[0].id, 'act': 'delete',
            'commentId': json_response_comment['id'],
        }, content_type='application/json')
        assert delete_response.status_code == 403

    @staticmethod
    def test_share_solution_by_another_user(
        exercise: Exercise,
        student_user: User,
    ):
        student_user2 = conftest.create_student_user(index=1)
        solution = conftest.create_solution(exercise, student_user2)

        client = conftest.get_logged_user(student_user.username)

        not_exist_share_response = client.post('/share', data=json.dumps({
            'solutionId': solution.id + 1, 'act': 'get',
        }), content_type='application/json')
        assert not_exist_share_response.status_code == 404

        not_user_solution_share_response = client.post(
            '/share', data=json.dumps({
                'solutionId': solution.id, 'act': 'get',
            }), content_type='application/json',
        )
        assert not_user_solution_share_response.status_code == 403

    @staticmethod
    def test_share_solution_function(
        exercise: Exercise,
        student_user: User,
    ):
        student_user2 = conftest.create_student_user(index=1)
        solution = conftest.create_solution(exercise, student_user2)

        client2 = conftest.get_logged_user(student_user2.username)
        # Sharing his own solution
        shared_response = client2.post('/share', data=json.dumps({
            'solutionId': solution.id, 'act': 'get',
        }), content_type='application/json')
        assert shared_response.status_code == 200

        # Unknown act of share
        unknown_shared_response = client2.post('/share', data=json.dumps({
            'solutionId': solution.id, 'act': 'unknown',
        }), content_type='application/json')
        assert unknown_shared_response.status_code == 400

        # Entering another student solution
        shared_url = SharedSolution.get_or_none(
            SharedSolution.solution == solution,
        )
        assert len(shared_url.entries) == 0
        conftest.logout_user(client2)
        client = conftest.get_logged_user(student_user.username)
        shared_response = client.get(f'{routes.SHARED}/{shared_url}')
        assert shared_response.status_code == 200
        assert len(shared_url.entries) == 1

        # Downloading another student solution by solution.id
        solution_id_download_response = client.get(
            f'{routes.DOWNLOADS}/{solution.id}',
        )
        assert solution_id_download_response.status_code == 403

        # Downloading another student solution
        download_response = client.get(
            f'{routes.DOWNLOADS}/{shared_url}',
        )
        assert download_response.status_code == 200

        # Deleting another user's solution
        delete_not_user_solution_response = client.post(
            '/share', data=json.dumps({
                'solutionId': solution.id, 'act': 'delete',
            }), content_type='application/json',
        )
        assert delete_not_user_solution_response.status_code == 403

        # Deleting his own solution
        conftest.logout_user(client)
        client2 = conftest.get_logged_user(student_user2.username)
        delete_share_response = client2.post('/share', data=json.dumps({
            'solutionId': solution.id, 'act': 'delete',
        }), content_type='application/json')
        assert delete_share_response.status_code == 200

        # Entering not shared solution after deletion
        conftest.logout_user(client2)
        client = conftest.get_logged_user(student_user.username)
        not_shared_solution_response = client.get(
            f'{routes.SHARED}/{shared_url}',
        )
        assert not_shared_solution_response.status_code == 404

    @staticmethod
    def test_share_with_disabled_shareable_solutions(
        solution: Solution,
        student_user: User,
    ):
        client = conftest.get_logged_user(student_user.username)
        conftest.disable_shareable_solutions()
        shared_response = client.post('/share', data=json.dumps({
            'solutionId': solution.id, 'act': 'get',
        }), content_type='application/json')
        assert shared_response.status_code == 403

    @staticmethod
    def test_shared_url_with_disabled_shared_solutions(
        solution: Solution,
        student_user: User,
    ):
        client = conftest.get_logged_user(student_user.username)
        shared_solution = conftest.create_shared_solution(solution)
        conftest.disable_shareable_solutions()
        not_shared_solution_response = client.get(
            f'{routes.SHARED}/{shared_solution}',
        )
        assert not_shared_solution_response.status_code == 404

    @staticmethod
    def test_view_page(
        exercise: Exercise,
        student_user: User,
    ):
        student_user2 = conftest.create_student_user(index=1)
        solution = conftest.create_solution(exercise, student_user)
        solution2 = conftest.create_solution(exercise, student_user2)

        client = conftest.get_logged_user(student_user.username)
        view_response = client.get(f'/view/{solution.id}')
        assert view_response.status_code == 200

        another_user_solution_response = client.get(f'/view/{solution2.id}')
        assert another_user_solution_response.status_code == 403

        not_exist_solution_response = client.get('/view/0')
        assert not_exist_solution_response.status_code == 404

    @staticmethod
    def test_strange_solution_with_no_files(
        exercise: Exercise,
        student_user: User,
        staff_user: User,
    ):
        solution = conftest.create_solution(
            exercise, student_user, files=[], hash_='koko',
        )

        staff_client = conftest.get_logged_user(staff_user.username)
        view_response = staff_client.get(f'{routes.SOLUTIONS}/{solution.id}')
        assert view_response.status_code == 200
        solution = Solution.get_by_id(solution.id)
        assert solution.state == Solution.STATES.DONE.name

        to_show_in_view = {
            'solution': solution,
            'file_id': None,
            'shared_url': '',
            'is_manager': False,
            'solution_files': (),
            'viewer_is_solver': True,
        }

        with pytest.raises(ResourceNotFound):
            assert get_view_parameters(**to_show_in_view)

        user_client = conftest.get_logged_user(student_user.username)
        assert len(list(notifications.get(student_user))) == 1
        view_response = user_client.get(f'{routes.SOLUTIONS}/{solution.id}')
        assert view_response.status_code == 404

    @staticmethod
    def test_manager_can_see_solutions(
        solution: Solution,
        staff_user: User,
    ):
        staff_client = conftest.get_logged_user(staff_user.username)
        view_response = staff_client.get(f'{routes.SOLUTIONS}/{solution.id}')
        assert view_response.status_code == 200
