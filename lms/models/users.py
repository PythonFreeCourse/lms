import re

from flask_babel import gettext as _  # type: ignore
from itsdangerous import URLSafeTimedSerializer

from lms.lmsdb.models import Course, User, UserCourse
from lms.lmsweb import config
from lms.models.errors import (
    AlreadyExists, ForbiddenPermission, UnauthorizedError,
    UnhashedPasswordError,
)


SERIALIZER = URLSafeTimedSerializer(config.SECRET_KEY)
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
