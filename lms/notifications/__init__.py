import typing

from lms.lmsdb import models
from lms.notifications import base
from lms.notifications.solution_checked import (
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
            models.Notification.marked_read.name:
                notification.marked_read,
            models.Notification.message_parameters.name:
                notification.message_parameters,
            models.Notification.notification_type.name:
                notification.notification_type,
        }
        for notification
        in models.Notification.notifications_for_user(for_user)
    )


def mark_as_read(
        from_user: models.User,
        notification_id: typing.Optional[int] = 0,
) -> bool:
    # explicit notification
    if notification_id:
        try:
            notification = models.Notification.get_by_id(notification_id)
        except models.Notification.DoesNotExist:
            return False

        if notification.user.id != from_user.id:
            return False

        notification.mark_as_read()
        return True

    # all notifications of the user
    for notification in models.Notification.notifications_for_user(from_user):
        notification.mark_as_read()
    return True


__all__ = (
    get_notifications_for_user.__name__,
    mark_as_read.__name__,
) + tuple(_MAPPING.keys())
