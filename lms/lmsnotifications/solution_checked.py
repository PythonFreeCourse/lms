from lms.lmsdb import models
from lms.lmsnotifications import base


class SolutionCheckedNotification(base.BaseNotification):
    @staticmethod
    def build_parameters_for_db(solution: models.Solution, **kwargs):
        return {
            'exercise_name': solution.exercise.subject,
        }

    @staticmethod
    def build_related_object_id(solution: models.Solution, **kwargs):
        return solution.id

    def get_text_template(self) -> str:
        return 'תרגיל {exercise_name} נבדק. צפה בתוצאות!'


class SolutionWithFlake8Errors(base.BaseNotification):
    @staticmethod
    def build_parameters_for_db(solution: models.Solution, errors: int):
        return {
            'exercise_name': solution.exercise.subject,
            'errors': errors,
        }

    @staticmethod
    def build_related_object_id(solution: models.Solution, **kwargs):
        return solution.id

    def get_text_template(self) -> str:
        return 'נמצאו {errors} תקלות בבדיקה האוטומטית עבור התרגיל {exercise_name}'  # NOQA: E501
