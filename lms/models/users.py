import asyncio
from functools import partial
import os
import re
from uuid import uuid4

from flask_babel import gettext as _  # type: ignore
from itsdangerous import URLSafeTimedSerializer
from PIL import Image
from werkzeug.datastructures import FileStorage

from lms.lmsdb.models import Course, User, UserCourse
from lms.lmsweb import avatars_path, config
from lms.models.errors import (
    AlreadyExists, ForbiddenPermission, UnauthorizedError,
    UnhashedPasswordError, UnprocessableRequest,
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


def create_avatar_filename(form_picture: FileStorage) -> str:
    __, extension = os.path.splitext(form_picture.filename)
    if not extension:
        raise UnprocessableRequest(_("Empty filename isn't allowed"), 422)
    filename = str(uuid4())
    return filename + extension


def save_avatar(form_picture: FileStorage, filename: str) -> None:
    avatar_path = avatars_path / filename
    output_size = (125, 125)
    image = Image.open(form_picture)
    image.thumbnail(output_size)
    image.save(avatar_path)


async def async_avatars_proccess(form_picture: FileStorage, filename: str):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None, partial(save_avatar, form_picture, filename),
    )


async def avatars_handler(form_picture: FileStorage, filename: str):
    asyncio.create_task(async_avatars_proccess(form_picture, filename))


def delete_previous_avatar(avatar_name: str) -> None:
    avatar_path = avatars_path / avatar_name
    avatar_path.unlink(missing_ok=True)


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
