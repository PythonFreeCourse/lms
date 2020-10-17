from typing import Optional

from flask import request
from flask_login import current_user  # type: ignore
from peewee import fn  # type: ignore

from lms.lmsdb.models import (
    Comment, CommentText, Exercise, Role, Solution, SolutionFile, User,
)
from lms.models import solutions
from lms.models.errors import (
    ForbiddenPermission, NotValidRequest, ResourceNotFound,
    UnprocessableRequest,
)


def _create_comment(
    user: User,
    file: SolutionFile,
    kind: str,
    line_number: int,
    comment_text: Optional[str] = None,  # set when kind == text
    comment_id: Optional[int] = None,  # set when kind == id
):
    if user is None:
        # should never happen, we checked session_id == solver_id
        raise ResourceNotFound('No such user.', 404)

    if (not kind) or (kind not in ('id', 'text')):
        raise NotValidRequest('Invalid kind.', 400)

    if line_number <= 0:
        raise UnprocessableRequest(f'Invalid line number: {line_number}.', 422)

    if kind == 'id':
        new_comment_id = comment_id
    elif kind == 'text':
        if not comment_text:
            raise UnprocessableRequest('Empty comments are not allowed.', 422)
        new_comment_id = CommentText.create_comment(text=comment_text).id
    else:
        # should never happend, kind was checked before
        raise NotValidRequest('Invalid kind.', 400)

    solutions.notify_comment_after_check(user, file.solution)

    return Comment.create(
        commenter=user,
        line_number=line_number,
        comment=new_comment_id,
        file=file,
    )


def delete():
    comment_id = int(request.args.get('commentId'))
    comment_ = Comment.get_or_none(Comment.id == comment_id)
    if (
        comment_.commenter.id != current_user.id
        and not current_user.role.is_manager
    ):
        raise ForbiddenPermission(
            "You aren't allowed to access this page.", 403,
        )
    if comment_ is not None:
        comment_.delete_instance()


def create(file: SolutionFile, user: User):
    kind = request.json.get('kind', '')
    comment_id, comment_text = None, None
    try:
        line_number = int(request.json.get('line', 0))
    except ValueError:
        line_number = 0
    if kind.lower() == 'id':
        comment_id = int(request.json.get('comment', 0))
    if kind.lower() == 'text':
        comment_text = request.json.get('comment', '')
    return _create_comment(
        user,
        file,
        kind,
        line_number,
        comment_text,
        comment_id,
    )


def _common_comments(exercise_id=None, user_id=None):
    """
    Most common comments throughout all exercises.
    Filter by exercise id when specified.
    """
    is_moderator_comments = (
        (Comment.commenter.role == Role.get_staff_role().id)
        | (Comment.commenter.role == Role.get_admin_role().id),
    )
    query = (
        CommentText.select(CommentText.id, CommentText.text)
        .join(Comment).join(User).join(Role).where(
            CommentText.flake8_key.is_null(True),
            is_moderator_comments,
        ).switch(Comment)
    )

    if exercise_id is not None:
        query = (
            query
            .join(SolutionFile)
            .join(Solution)
            .join(Exercise)
            .where(Exercise.id == exercise_id)
        )

    if user_id is not None:
        query = (
            query
            .filter(Comment.commenter == user_id)
        )

    query = (
        query
        .group_by(CommentText.id)
        .order_by(fn.Count(CommentText.id).desc())
        .limit(5)
    )

    return tuple(query.dicts())
