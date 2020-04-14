from lms.lmsdb import models
from lms.notifications import base


class SolutionCheckedNotification(base.BaseNotification):
    @staticmethod
    def build_parameters_for_db(solution: models.Solution, **kwargs):
        return {
            'exercise_name': solution.exercise.subject,
        }

    @staticmethod
    def build_related_object_id(solution: models.Solution, **kwargs):
        return solution.id


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
