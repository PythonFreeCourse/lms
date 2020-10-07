import random
import string

from flask import json
import pytest  # type: ignore

from lms.lmsdb.models import Exercise, Notification, Solution, User
from lms.models import notifications, solutions
from lms.tests import conftest


class TestNotification:
    kind_checked = notifications.NotificationKind.CHECKED
    kind_flake8 = notifications.NotificationKind.FLAKE8_ERROR

    @classmethod
    def generate_params(cls):
        related_id = random.randrange(2)  # NOQA: S311
        return {
            'kind': random.choice((cls.kind_checked, cls.kind_flake8)),  # NOQA: E501, S311
            'message': ''.join(random.choices(string.printable, k=100)),
            'related_id': related_id,
            'action_url': f'/view/{related_id}',
        }

    @staticmethod
    def create_too_many_notifications(user: User, solut: Solution):
        for i in range(Notification.MAX_PER_USER + 5):
            conftest.create_notification(user, solut, index=i)

    @staticmethod
    def check_full_inbox(user: User):
        assert (
            len(list(notifications.get(user))) == Notification.MAX_PER_USER
        )

    @staticmethod
    def check_viewed_inbox(user: User):
        with pytest.raises(Notification.DoesNotExist):
            Notification.get(user=user, viewed=False)

    @staticmethod
    def get_unread(user: User):
        return (
            Notification
            .select()
            .where(
                Notification.user == user,
                Notification.viewed == False,  # NOQA: E712
            )
        )

    def test_get(
            self,
            student_user: User,
            notification: Notification,
            solution: Solution,
    ):
        assert len(list(notifications.get(student_user))) == 1

        n = next(iter(notifications.get(student_user)), None)
        assert n is not None
        assert n.user == student_user
        assert n.related_id == solution.id
        assert n.message == 'Test message 0'

        student_user2 = conftest.create_student_user(index=1)
        assert len(list(notifications.get(student_user2))) == 0
        conftest.create_notification(student_user2, solution, index=2)
        assert len(list(notifications.get(student_user))) == 1
        assert len(list(notifications.get(student_user2))) == 1

        self.create_too_many_notifications(student_user, solution)
        assert (
            len(list(notifications.get(student_user)))
            == Notification.MAX_PER_USER
        )

    def test_read(
            self,
            student_user: User,
            solution: Solution,
    ):
        assert len(list(notifications.get(student_user))) == 0
        message_id = conftest.create_notification(student_user, solution)
        assert len(list(notifications.get(student_user))) == 1
        unread = self.get_unread(student_user)
        assert len(list(unread)) == 1
        notifications.read(id_=message_id)
        self.check_viewed_inbox(student_user)

        # Test by notification ID
        self.create_too_many_notifications(student_user, solution)
        assert (
            len(list(notifications.get(student_user)))
            == Notification.MAX_PER_USER
        )
        for notification in notifications.get(student_user):
            success = notifications.read(id_=notification.id)
            assert success
        self.check_full_inbox(student_user)  # Still there
        self.check_viewed_inbox(student_user)  # But already viewed

        # Test by user
        self.create_too_many_notifications(student_user, solution)
        assert (
            len(list(notifications.get(student_user)))
            == Notification.MAX_PER_USER
        )
        notifications.read(user=student_user)
        self.check_full_inbox(student_user)  # Still there
        self.check_viewed_inbox(student_user)  # But already viewed

    def test_read_related(
            self, student_user: User, solution: Solution, exercise: Exercise,
    ):
        solution2 = conftest.create_solution(student_user, exercise)
        student_user2 = conftest.create_user(index=1)
        messages = [
            conftest.create_notification(student_user, solution),
            conftest.create_notification(student_user, solution),
            conftest.create_notification(student_user, solution),
            conftest.create_notification(student_user, solution2),
            conftest.create_notification(student_user2, solution),
        ]
        assert all(not n.viewed for n in messages)
        notifications.read_related(solution.id, student_user)
        # peewee...
        messages = [Notification.get_by_id(n.id) for n in messages]
        assert all(n.viewed for n in messages[:3])
        assert all(not n.viewed for n in messages[3:])

    def test_send(self, student_user: User):
        another_user = conftest.create_student_user(index=1)
        params = self.generate_params()
        n1 = notifications.send(student_user, **params)
        n2 = notifications.send(another_user, self.kind_checked, 'yoyo2')
        n3 = notifications.send(student_user, self.kind_flake8, 'yoyo3')

        assert n1.user == student_user
        assert n1.kind == params['kind'].value
        assert n1.message == params['message']
        assert n1.related_id == params['related_id']
        assert n1.action_url == params['action_url']
        assert n2.kind != n3.kind
        assert n2.message == 'yoyo2'
        assert n2.user == another_user
        assert len(list(notifications.get(student_user))) == 2
        assert len(list(notifications.get(another_user))) == 1

    def test_auto_deletion(self, student_user: User):
        extra = 3
        start = Notification.MAX_PER_USER
        for _ in range(Notification.MAX_PER_USER + extra - 1):
            notifications.send(
                user=student_user,
                kind=notifications.NotificationKind.CHECKED,
                message='',
                related_id=1,
                action_url='/view/1',
            )

        assert Notification.select().count() == start
        expected = start + extra - 1
        actual = Notification.select().order_by(
            Notification.created.desc()).get().id
        assert expected == actual

    @staticmethod
    def test_user_commented_after_check(
        solution: Solution,
        student_user: User,
        staff_user: User,
    ):
        client = conftest.get_logged_user(student_user.username)

        # Marking the solution as checked
        solutions.mark_as_checked(solution.id, staff_user.id)
        solution = Solution.get_by_id(solution.id)

        # Sending comments after solution checked
        comment_response = client.post('/comments', data=json.dumps({
            'fileId': solution.files[0].id, 'act': 'create', 'kind': 'text',
            'comment': 'new one', 'line': 1,
        }), content_type='application/json')
        new_comment_response = client.post('/comments', data=json.dumps({
            'fileId': solution.files[0].id, 'act': 'create', 'kind': 'text',
            'comment': 'another one', 'line': 2,
        }), content_type='application/json')
        assert comment_response.status_code == 200
        assert new_comment_response.status_code == 200
        assert len(list(notifications.get(staff_user))) == 1

        conftest.logout_user(client)
        client2 = conftest.get_logged_user(staff_user.username)

        # Sending a comment after student user commented
        staff_comment_response = client2.post(
            '/comments', data=json.dumps({
                'fileId': solution.files[0].id, 'act': 'create',
                'kind': 'text', 'comment': 'FINE', 'line': 1,
            }), content_type='application/json',
        )
        assert staff_comment_response.status_code == 200
        assert len(list(notifications.get(student_user))) == 2

        conftest.logout_user(client2)
        client = conftest.get_logged_user(student_user.username)

        # User student comments again
        another_comment_response = client.post(
            '/comments', data=json.dumps({
                'fileId': solution.files[0].id, 'act': 'create',
                'kind': 'text', 'comment': 'OK', 'line': 3,
            }), content_type='application/json',
        )
        assert another_comment_response.status_code == 200
        assert len(list(notifications.get(staff_user))) == 2
