from flask import json

from lms.lmsdb.models import User
from tests import conftest


class TestNotes:
    @staticmethod
    def test_notes(
        staff_user: User,
        student_user: User,
    ):
        staff_user2 = conftest.create_staff_user(index=1)

        private_note, _ = conftest.create_note(
            creator=staff_user,
            user=student_user,
            note_text='private note',
            privacy=0,
        )
        staff_note, _ = conftest.create_note(
            creator=staff_user,
            user=student_user,
            note_text='staff note',
            privacy=1,
        )
        user_note, _ = conftest.create_note(
            creator=staff_user,
            user=student_user,
            note_text='user note',
            privacy=2,
        )
        public_note, _ = conftest.create_note(
            creator=staff_user,
            user=student_user,
            note_text='public note',
            privacy=3,
        )

        client = conftest.get_logged_user(staff_user2.username)
        # Trying to remove a private note of another staff client
        private_note_response = client.get(
            f'/notes/{student_user.id}',
            query_string={'noteId': private_note.id},
            data=json.dumps({'act': 'delete'}),
            content_type='application/json',
        )
        assert private_note_response.status_code == 403

        # Removing a staff note of another staff user
        staff_note_response = client.get(
            f'/notes/{student_user.id}',
            query_string={'noteId': staff_note.id},
            data=json.dumps({'act': 'delete'}),
            content_type='application/json',
        )
        assert staff_note_response.status_code == 200

        # Another staff user can see only the remaining user and public comment
        user_page_notes = client.get(
            f'notes/{student_user.id}', query_string={'act': 'fetch'},
            content_type='application/json',
        )
        json_user_page_notes = json.loads(
            user_page_notes.get_data(as_text=True),
        )
        assert len(json_user_page_notes) == 2

        conftest.logout_user(client)
        client2 = conftest.get_logged_user(student_user.username)
        # User can see only the remaining user and public comment
        user_page_notes = client2.get(
            f'notes/{student_user.id}', query_string={'act': 'fetch'},
            content_type='application/json',
        )
        json_user_page_notes = json.loads(
            user_page_notes.get_data(as_text=True),
        )
        assert len(json_user_page_notes) == 2

        # Trying to remove a public note
        public_note_response = client2.get(
            f'/notes/{student_user.id}',
            query_string={'noteId': public_note.id},
            data=json.dumps({'act': 'delete'}),
            content_type='application/json',
        )
        assert public_note_response.status_code == 403

        # User trying to create a note, doesn't matter what
        new_note_response = client2.post(
            f'/notes/{student_user.id}',
            data=json.dumps({'act': 'create'}),
            content_type='application/json',
        )
        assert new_note_response.status_code == 403
