import re

from flask_babel import gettext as _  # type: ignore

from lms.lmsdb.models import User
from lms.models.errors import (
    ForbiddenPermission, UnauthorizedError, UnhashedPasswordError,
)


HASHED_PASSWORD = re.compile(r'^pbkdf2.+?\$(?P<salt>.+?)\$(?P<password>.+)')


def retrieve_salt(user: User) -> str:
    password = HASHED_PASSWORD.match(user.password)
    try:
        return password.groupdict().get('salt')
    except AttributeError:  # should never happen
        raise UnhashedPasswordError('Password format is invalid.')


def auth(username: str, password: str) -> User:
    user = User.get_or_none(username=username)
    if user is None or not user.is_password_valid(password):
        raise UnauthorizedError(_('שם המשתמש או הסיסמה שהוזנו לא תקינים'), 400)
    elif user.role.is_unverified:
        raise ForbiddenPermission(_('עליך לאשר את מייל האימות'), 403)
    return user
