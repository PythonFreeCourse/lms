from typing import Optional

from flask import jsonify, request
from flask_login import current_user

from lms.lmsdb.models import CommentText, Exercise, Note, NotePrivacy, User
from lms.models.errors import fail


def create_note_instance(
    creator: User,
    user: User,
    note_text: CommentText,
    privacy: NotePrivacy,
    exercise: Optional[Exercise] = None,
) -> Note:
    return Note.get_or_create(
        creator=creator,
        user=user,
        note=note_text,
        exercise=exercise,
        privacy=privacy,
    )


def delete_note():
    note_id = int(request.args.get('noteId'))
    note_ = Note.get_or_none(Note.id == note_id)
    if (
        note_.creator.id != current_user.id
        and note_.is_private
    ):
        return fail(403, "You aren't allowed to access this page.")
    if note_ is not None:
        note_.delete_instance()
    return jsonify({'success': 'true'})


def create_note(user: User, user_id: int):
    note_text = request.args.get('note', '')
    note_exercise = request.args.get('exercise', '')
    privacy = request.args.get('privacy')
    if not note_text:
        return fail(422, 'Empty notes are not allowed.')
    new_note_id = CommentText.create_comment(text=note_text).id

    note_ = Note.create(
        creator=User.get_or_none(User.id == current_user.id),
        user=user,
        note=new_note_id,
        exercise=Exercise.get_or_none(Exercise.subject == note_exercise),
        privacy=Note.get_privacy_level(int(privacy)),
    )
    return jsonify({
        'success': 'true', 'id': note_.id, 'fullname': note_.creator.fullname,
        'text': note_.note.text, 'timestamp': note_.timestamp,
        'exercise': note_.exercise,
    })
