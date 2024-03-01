import pytest

from lms.lmsdb.models import Comment, Solution, User
from lms.models import comments
from lms.models.errors import ForbiddenPermission, NotValidRequest
from tests.conftest import create_student_user


class TestComments:
    @staticmethod
    def test_comment_delete(
        comment: Comment, staff_user: User, solution: Solution,
    ):
        second_comment = Comment.create_comment(
            commenter=staff_user,
            line_number=1,
            comment_text="Yabalulu",
            file=solution.solution_files.get(),
            is_auto=False,
        )[0]
        assert Comment.get_or_none(comment.id)
        assert Comment.get_or_none(second_comment.id)
        comments.delete(
            comment_id=comment.id,
            request_user_id=staff_user.id,
            is_manager=True,
        )
        assert Comment.get_or_none(comment.id) is None
        assert Comment.get_or_none(second_comment.id)

    @staticmethod
    def test_comment_delete_invalid_comment_id():
        with pytest.raises(NotValidRequest):
            comments.delete(
                comment_id="Shawarma",  # type: ignore
                request_user_id=1,
            )

    @staticmethod
    def test_comment_delete_by_unexisting_user(comment: Comment):
        assert Comment.get_or_none(comment.id)
        with pytest.raises(ForbiddenPermission):
            comments.delete(
                comment_id=comment.id,
                request_user_id=50000,
            )

    @staticmethod
    def test_comment_delete_by_unprivileged_delete(comment: Comment):
        bad_user = create_student_user(index=500)
        assert Comment.get_or_none(comment.id)
        with pytest.raises(ForbiddenPermission):
            comments.delete(
                comment_id=comment.id,
                request_user_id=bad_user.id,
            )
