import typing

from lms.lmsdb import models
from lms.lmsnotifications import base
from lms.lmsnotifications.solution_checked import (
    SolutionCheckedNotification,
    SolutionWithFlake8Errors,
)

_ALL = (
    SolutionCheckedNotification,
    SolutionWithFlake8Errors,
)

_MAPPING = {
    notification_formatter.notification_type(): notification_formatter
    for notification_formatter in _ALL
}


def get_message_from_notification(notification: models.Notification) -> str:
    if notification.notification_type not in _MAPPING:
        raise NotImplementedError

    instance: base.BaseNotification = _MAPPING[
        notification.notification_type
    ](notification)
    return instance.format_message()


def create_notification(
        notification_type: str,
        for_user: models.User, **kwargs,
) -> None:
    if notification_type not in _MAPPING:
        raise NotImplementedError

    instance: base.BaseNotification = _MAPPING[notification_type]
    instance.create_notification(for_user=for_user, **kwargs)


def get_notifications_for_user(for_user: models.User) -> typing.Sequence[dict]:
    return tuple(
        {
            models.Notification.ID_FIELD_NAME:
                notification.id,
            models.Notification.user.name:
                notification.user.id,
            models.Notification.related_object_id.name:
                notification.related_object_id,
            models.Notification.MESSAGE_FIELD_NAME:
                get_message_from_notification(notification),
            models.Notification.marked_read.name:
                notification.marked_read,
        }
        for notification
        in models.Notification.notifications_for_user(for_user)
    )


def mark_as_read(
        from_user: models.User,
        notification_id: int,
) -> bool:
    try:
        notification = models.Notification.get_by_id(notification_id)
    except models.Notification.DoesNotExist:
        return False

    if notification.user.id != from_user.id:
        return False

    notification.mark_as_read()
    return True


__all__ = (
    get_message_from_notification.__name__,
    get_notifications_for_user.__name__,
    mark_as_read.__name__,
) + tuple(_MAPPING.keys())
