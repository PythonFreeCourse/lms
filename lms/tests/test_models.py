from lms.lmsdb.models import Exercise, Solution, User


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

    def test_new_solution_override_old_solutions(
            self,
            exercise: Exercise,
            student_user: User,
    ):
        first_solution = Solution.create_solution(exercise, student_user)
        second_solution = Solution.create_solution(exercise, student_user)
        assert second_solution.latest_solution
        assert not first_solution.get().latest_solution  # refresh results

        assert Solution.next_unchecked()['id'] == second_solution.id
        next_unchecked_id = Solution.next_unchecked_of(exercise.id)['id']
        assert next_unchecked_id == second_solution.id

        second_solution.is_checked = True
        second_solution.save()

        assert Solution.next_unchecked() == {}
        assert Solution.next_unchecked_of(exercise.id) == {}
