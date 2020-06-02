import datetime

from lms.lmsdb.models import Exercise


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
