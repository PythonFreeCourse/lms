from typing import Optional

from flask import jsonify
from peewee import fn  # type: ignore

from lms.lmsdb.models import (
    Comment, CommentText, Exercise, Role, Solution, SolutionFile, User,
)
from lms.models.errors import fail


def _create_comment(
    user_id: int,
    file: SolutionFile,
    kind: str,
    line_number: int,
    comment_text: Optional[str] = None,  # set when kind == text
    comment_id: Optional[int] = None,  # set when kind == id
):
    user = User.get_or_none(User.id == user_id)
    if user is None:
        # should never happen, we checked session_id == solver_id
        return fail(404, 'No such user.')

    if (not kind) or (kind not in ('id', 'text')):
        return fail(400, 'Invalid kind.')

    if line_number <= 0:
        return fail(422, f'Invalid line number: {line_number}.')

    if kind == 'id':
        new_comment_id = comment_id
    elif kind == 'text':
        if not comment_text:
            return fail(422, 'Empty comments are not allowed.')
        new_comment_id = CommentText.create_comment(text=comment_text).id
    else:
        # should never happend, kind was checked before
        return fail(400, 'Invalid kind.')

    comment_ = Comment.create(
        commenter=user,
        line_number=line_number,
        comment=new_comment_id,
        file=file,
    )

    return jsonify({
        'success': 'true', 'text': comment_.comment.text,
        'author_name': user.fullname, 'author_role': user.role.id,
        'is_auto': False, 'id': comment_.id, 'line_number': line_number,
    })


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
