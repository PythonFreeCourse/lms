from unittest import mock

from lms.lmsdb.models import Comment, Exercise, Solution, User
from lms.lmstests.public.general import tasks as general_tasks
from lms.models import notifications, solutions
from lms.tests import conftest


celery_async = (
    'lms.lmstests.public.general.tasks'
    '.reset_solution_state_if_needed.apply_async'
)
no_celery = mock.patch(celery_async, lambda *args, **kwargs: None)


class TestSolutionDb:
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

        next_unchecked = Solution.next_unchecked()
        assert next_unchecked is not None
        assert next_unchecked.id == second_solution.id
        next_unchecked = Solution.next_unchecked_of(exercise.id)
        assert next_unchecked is not None
        assert next_unchecked.id == second_solution.id
        assert next_unchecked.start_checking()
        assert next_unchecked.refresh().state == self.in_checking_state

        assert Solution.next_unchecked() is None
        assert Solution.next_unchecked_of(exercise.id) is None

        general_tasks.reset_solution_state_if_needed(second_solution.id)
        next_unchecked = Solution.next_unchecked()
        next_unchecked_by_id = Solution.next_unchecked_of(exercise.id)
        assert next_unchecked is not None and next_unchecked_by_id is not None
        assert next_unchecked.id == second_solution.id
        assert next_unchecked_by_id.id == second_solution.id

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
        next_unchecked = Solution.next_unchecked()
        assert next_unchecked is not None
        assert next_unchecked.id == second_solution.id

        # delete the comment should give us back the first solution
        Comment.delete_by_id(comment.id)
        next_unchecked = Solution.next_unchecked()
        assert next_unchecked is not None
        assert next_unchecked.id == first_solution.id

        # if second_solution has comments we should get first solution
        Comment.create_comment(
            commenter=staff_user,
            line_number=1,
            comment_text=comment_text,
            solution=second_solution,
            is_auto=False,
        )
        next_unchecked = Solution.next_unchecked()
        assert next_unchecked is not None
        assert next_unchecked.id == first_solution.id

        # both have comments - the first one should be the first solution
        Comment.create_comment(
            commenter=staff_user,
            line_number=1,
            comment_text=comment_text,
            solution=first_solution,
            is_auto=False,
        )
        next_unchecked = Solution.next_unchecked()
        assert next_unchecked is not None
        assert next_unchecked.id == first_solution.id


class TestSolutionBridge:
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
