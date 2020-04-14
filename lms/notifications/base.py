import abc

from lms.lmsdb import models


class BaseNotification(abc.ABC):
    def __init__(self, notification: models.Notification):
        self.notification = notification

    @classmethod
    def notification_type(cls) -> str:
        return cls.__name__

    @staticmethod
    @abc.abstractmethod
    def build_parameters_for_db(**kwargs):
        pass

    @staticmethod
    @abc.abstractmethod
    def build_related_object_id(**kwargs) -> int:
        pass

    @classmethod
    def create_notification(cls, for_user: models.User, **kwargs) -> None:
        message_parameters = cls.build_parameters_for_db(**kwargs)
        models.Notification.create_notification(
            user=for_user,
            notification_type=cls.notification_type(),
            message_parameters=message_parameters,
            related_object_id=cls.build_related_object_id(**kwargs),
        )
