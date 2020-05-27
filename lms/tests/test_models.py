import datetime

from lms.lmsdb.models import Comment, Exercise, Notification, Solution, User
from lms.models import notifications
from lms.lmstests.public.general import tasks as general_tasks
from lms.tests import conftest


class TestUser:

    def test_password_hashed_on_create(
        self,
        staff_user: User,
        staff_password: str,
    ):
        self.assert_password(staff_user, staff_password)

    def test_password_hashed_on_save(self, staff_user: User):
        new_password = 'woop'  # noqa S105
        staff_user.password = new_password
        staff_user.save()
        self.assert_password(staff_user, new_password)

    def test_password_hashed_on_mmultiple_saves(self, staff_user: User):
        new_password = 'woop2'  # noqa S105
        staff_user.password = new_password
        staff_user.save()
        staff_user.save()
        self.assert_password(staff_user, new_password)
        staff_user.save()
        self.assert_password(staff_user, new_password)

    @staticmethod
    def assert_password(user, password):
        assert user.password != password
        assert password not in user.password
        assert user.is_password_valid(password)


class TestSolution:
    old_solution_state = Solution.STATES.OLD_SOLUTION.name
    in_checking_state = Solution.STATES.IN_CHECKING.name
    created_state = Solution.STATES.CREATED.name

    def test_new_solution_override_old_solutions(
            self,
            exercise: Exercise,
            student_user: User,
    ):
        first_solution = Solution.create_solution(exercise, student_user)
        second_solution = Solution.create_solution(exercise, student_user)
        assert second_solution.state == self.created_state
        assert first_solution.refresh().state == self.old_solution_state

        assert Solution.next_unchecked().id == second_solution.id
        next_unchecked = Solution.next_unchecked_of(exercise.id)
        assert next_unchecked.id == second_solution.id
        assert next_unchecked.start_checking()
        assert next_unchecked.refresh().state == self.in_checking_state

        assert Solution.next_unchecked() is None
        assert Solution.next_unchecked_of(exercise.id) is None
        general_tasks.reset_solution_state_if_needed(
            second_solution.id)
        assert Solution.next_unchecked().id == second_solution.id
        assert Solution.next_unchecked_of(exercise.id).id == second_solution.id

    def test_next_exercise_with_cleanest_code(
            self,
            comment: Comment,
            staff_user: User,
    ):
        student_user: User = conftest.create_student_user(index=1)
        first_solution = comment.solution
        comment_text = comment.comment
        second_solution = Solution.create_solution(
            comment.solution.exercise, student_user)

        # comment exists on first solution - second one should be the first
        assert Solution.next_unchecked().id == second_solution.id

        # delete the comment should give us back the first solution
        Comment.delete_by_id(comment.id)
        assert Solution.next_unchecked().id == first_solution.id

        # if second_solution has comments we should get first solution
        Comment.create_comment(
            commenter=staff_user,
            line_number=1,
            comment_text=comment_text,
            solution=second_solution,
            is_auto=False,
        )
        assert Solution.next_unchecked().id == first_solution.id

        # both have comments - the first one should be the first solution
        Comment.create_comment(
            commenter=staff_user,
            line_number=1,
            comment_text=comment_text,
            solution=first_solution,
            is_auto=False,
        )
        assert Solution.next_unchecked().id == first_solution.id


class TestNotification:
    def test_notification_auto_deletion(self, student_user: User):
        extra = 3
        start = Notification.MAX_PER_USER
        for _ in range(Notification.MAX_PER_USER + extra - 1):
            notifications.send(
                user=student_user,
                kind=notifications.NotificationKind.CHECKED,
                message='',
                related_id=1,
                action_url=1,
            )

        assert Notification.select().count() == start
        expected = start + extra - 1
        actual = Notification.select().order_by(
            Notification.created.desc()).get().id
        assert expected == actual


class TestExercise:
    def test_due_date(self, exercise: Exercise):
        assert exercise.open_for_new_solutions()
        exercise.is_archived = True
        exercise.save()
        assert not exercise.open_for_new_solutions()

        exercise.is_archived = False
        later_due_date = datetime.datetime.now() - datetime.timedelta(hours=1)
        exercise.due_date = later_due_date
        exercise.save()
        assert not exercise.open_for_new_solutions()

        after_due_date = datetime.datetime.now() + datetime.timedelta(hours=1)
        exercise.due_date = after_due_date
        exercise.save()
        assert exercise.open_for_new_solutions()
