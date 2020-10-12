from flask import json

from lms.lmsdb.models import Exercise, User
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

        # Staff trying unknown act
        unknown_act_note_response = client.post(
            f'/notes/{student_user.id}',
            data=json.dumps({'act': 'unknown'}),
            content_type='application/json',
        )
        assert unknown_act_note_response.status_code == 400

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

    @staticmethod
    def test_user_notes(student_user: User):
        client = conftest.get_logged_user(student_user.username)
        # User trying to create a note, doesn't matter what
        new_note_response = client.post(
            f'/notes/{student_user.id}',
            data=json.dumps({'act': 'create'}),
            content_type='application/json',
        )
        assert new_note_response.status_code == 403

        # Trying to reach not exist user
        not_exist_user_note_response = client.get(
            '/notes/99', data=json.dumps({'act': 'fetch'}),
            content_type='application/json',
        )
        assert not_exist_user_note_response.status_code == 404

    @staticmethod
    def test_create_note(
        student_user: User,
        staff_user: User,
        exercise: Exercise
    ):
        client = conftest.get_logged_user(staff_user.username)
        # Trying to create note with no text
        new_note_response = client.post(
            f'/notes/{student_user.id}',
            data=json.dumps({'act': 'create'}),
            query_string={'note': ''},
            content_type='application/json',
        )
        assert new_note_response.status_code == 422

        # Creating a staff note
        staff_note_response = client.post(
            f'/notes/{student_user.id}',
            data=json.dumps({'act': 'create'}),
            query_string={'note': 'staff note', 'privacy': '1'},
            content_type='application/json',
        )
        assert staff_note_response.status_code == 200

        # Creating a private note
        private_note_response = client.post(
            f'/notes/{student_user.id}',
            data=json.dumps({'act': 'create'}),
            query_string={'note': 'private note', 'exercise': exercise.subject},
            content_type='application/json',
        )
        assert private_note_response.status_code == 200

        # Fetching notes
        user_page_notes = client.get(
            f'notes/{student_user.id}', query_string={'act': 'fetch'},
            content_type='application/json',
        )
        json_user_page_notes = json.loads(
            user_page_notes.get_data(as_text=True),
        )
        staff_note, private_note = json_user_page_notes
        assert staff_note.get('privacy') == 30
        assert private_note.get('privacy') == 40
        assert private_note.get('subject') == exercise.subject
        assert staff_note.get('fullname') == staff_user.fullname
