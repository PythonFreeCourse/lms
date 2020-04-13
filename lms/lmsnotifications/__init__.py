import typing

from lms.lmsdb import models

from lms.lmsnotifications import base
from lms.lmsnotifications.solution_checked import (
    SolutionCheckedNotification,
    SolutionWithFlake8Errors,
)

_ALL = (
    SolutionCheckedNotification,
    SolutionWithFlake8Errors
)

_MAPPING = {
    notification_formatter.notification_type(): notification_formatter
    for notification_formatter in _ALL
}


def get_message_from_notification(notification: models.Notification) -> str:
    if notification.notification_type not in _MAPPING:
        raise NotImplementedError

    instance: base.BaseNotification = _MAPPING[notification.notification_type](notification)
    return instance.format_message()


def create_notification(notification_type: str, for_user: models.User, **kwargs) -> None:
    if notification_type not in _MAPPING:
        raise NotImplementedError

    instance: base.BaseNotification = _MAPPING[notification_type]
    instance.create_notification(for_user=for_user, **kwargs)


def get_messages_for_user(for_user: models.User) -> typing.Sequence[dict]:
    return tuple(
        {
            models.Notification.user.name:
                notification.user.id,
            models.Notification.related_object_id.name:
                notification.related_object_id,
            models.Notification.MESSAGE_FIELD_NAME:
                get_message_from_notification(notification)
        }
        for notification in models.Notification.notifications_for_user(for_user)
    )


__all__ = (
              get_message_from_notification.__name__,
              get_messages_for_user.__name__,
          ) + tuple(_MAPPING.keys())
