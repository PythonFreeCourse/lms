import enum
from typing import Iterable, Optional

from lms.lmsdb.models import Notification, User


class NotificationKind(enum.Enum):
    CHECKED = 1
    FLAKE8_ERROR = 2
    UNITTEST_ERROR = 2


def get(user: User) -> Iterable[Notification]:
    return Notification.fetch(user)


def read(user: Optional[User] = None, id_: Optional[int] = None) -> bool:
    if id_:
        try:
            notification = Notification.get_by_id(id_)
        except Notification.DoesNotExist:
            return False

        if user and (user.id != notification.user.id):
            return False

        notification.read()
        return True

    assert user, 'Must provide user or id_'  # noqa: B101, S101
    is_success = [msg.read() for msg in Notification.fetch(user)]
    return all(is_success)  # Not gen to prevent lazy evaluation


def read_related(related_id: int, user: int):
    for n in Notification.of(related_id, user):
        n.read()


def send(
        user: User,
        kind: NotificationKind,
        message: str,
        related_id: Optional[int] = None,
        action_url: Optional[str] = None,
) -> bool:
    return Notification.send(
        user, kind.value, message, related_id, action_url,
    )
