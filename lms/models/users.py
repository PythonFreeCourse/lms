from functools import cache
import hashlib
import re
from typing import cast

from flask_babel import gettext as _
from itsdangerous import URLSafeTimedSerializer

from lms.lmsdb.models import Course, User, UserCourse
from lms.lmsweb import config
from lms.models.errors import (
    AlreadyExists, ForbiddenPermission, NotValidRequest, ResourceNotFound,
    UnauthorizedError, UnhashedPasswordError,
)


SERIALIZER = URLSafeTimedSerializer(config.SECRET_KEY)
HASHED_PASSWORD = re.compile(
    r"^(?:scrypt|pbkdf2)"
    r".+?\$"
    r"(?P<salt>.+?)\$"
    r"(?P<password>.+)",
)


def _to_user_object(user: int | User) -> User:
    if isinstance(user, int):
        user = cast(User, User.get_or_none(User.id == user))
        if user is None:
            raise ResourceNotFound(_('User not found'), 404)

    if not isinstance(user, User):
        raise NotValidRequest(_('User is not valid'), 400)

    return user


def retrieve_salt(user: User) -> str:
    if password := HASHED_PASSWORD.match(str(user.password)):
        return password.groupdict()['salt']
    else:
        raise UnhashedPasswordError('Password format is invalid.')


def auth(username: str, password: str) -> User:
    user = User.get_or_none(username=username)
    if user is None or not user.is_password_valid(password):
        raise UnauthorizedError(_('Invalid username or password'), 400)
    elif user.role.is_unverified:
        raise ForbiddenPermission(
            _(
                'You have to confirm your registration with the link sent '
                'to your email',
            ), 403,
        )
    return user


def generate_user_token(user: User) -> str:
    return SERIALIZER.dumps(user.mail_address, salt=retrieve_salt(user))


def join_public_course(course: Course, user: User) -> None:
    __, created = UserCourse.get_or_create(**{
        UserCourse.user.name: user, UserCourse.course.name: course,
    })
    if not created:
        raise AlreadyExists(
            _(
                'You are already registered to %(course_name)s course.',
                course_name=course.name,
            ), 409,
        )


@cache
def get_gravatar(user: int | User) -> str:
    user = _to_user_object(user)
    user_email = str(user.mail_address).strip().lower()
    gravatar_hash = hashlib.sha256(user_email.encode('utf-8')).hexdigest()
    return f'https://www.gravatar.com/avatar/{gravatar_hash}?d=404'
