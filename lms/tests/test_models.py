import random
import string
from unittest import mock

import pytest

from lms.lmsdb.models import Exercise, Notification, Solution, User
from lms.models import notifications, solutions
from lms.tests import conftest


celery_async = (
    'lms.lmstests.public.general.tasks'
    '.reset_solution_state_if_needed.apply_async'
)
no_celery = mock.patch(celery_async, lambda *args, **kwargs: None)


class TestSolution2:
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
        solution2 = Solution.create_solution(exercise, student_user)
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
    def test_start_checking(
            exercise: Exercise,
            student_user: User,
            staff_user: User,
    ):
        student_user2 = conftest.create_student_user(index=1)
        exercise2 = conftest.create_exercise(1)
        solution1 = Solution.create_solution(exercise, student_user)
        solution2 = Solution.create_solution(exercise2, student_user)
        solution3 = Solution.create_solution(exercise, student_user2)

        is_checking = solutions.start_checking(solution=None)
        assert not is_checking

        with no_celery:
            for solution in (solution1, solution2, solution3):
                assert solution.state == Solution.STATES.CREATED.name
                is_checking = solutions.start_checking(solution=solution)
                assert is_checking
                the_solution = Solution.get_by_id(solution.id)
                assert the_solution.state == Solution.STATES.IN_CHECKING.name


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
