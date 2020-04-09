from lms.lmsdb.models import Exercise, Solution, User
from lms.lmstests.public.general import tasks as general_tasks


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
