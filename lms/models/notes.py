from flask import jsonify, request
from flask_login import current_user

from lms.lmsdb.models import CommentText, Exercise, Note, User
from lms.models.errors import fail


def delete():
    note_id = int(request.args.get('noteId'))
    note_ = Note.get_or_none(Note.id == note_id)
    if note_.creator.id != current_user.id and note_.is_private:
        return fail(403, "You aren't allowed to access this page.")
    if note_ is not None:
        note_.delete_instance()
    return jsonify({'success': 'true'})


def create(user: User) -> Note:
    note_text = request.args.get('note', '')
    note_exercise = request.args.get('exercise', '')
    privacy = request.args.get('privacy')
    if not note_text:
        return fail(422, 'Empty notes are not allowed.')
    new_note_id = CommentText.create_comment(text=note_text).id

    return Note.create(
        creator=User.get_or_none(User.id == current_user.id),
        user=user,
        note=new_note_id,
        exercise=Exercise.get_or_none(Exercise.subject == note_exercise),
        privacy=Note.get_privacy_level(int(privacy)),
    )
