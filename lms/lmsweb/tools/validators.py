from typing import TYPE_CHECKING

from flask_babel import gettext as _  # type: ignore
from wtforms import StringField
from wtforms.validators import ValidationError

from lms.lmsdb.models import User

if TYPE_CHECKING:
    from lms.lmsweb.forms.register import RegisterForm
    from lms.lmsweb.forms.reset_password import ResetPassForm


def UniqueUsernameRequired(__: 'RegisterForm', field: StringField) -> None:
    username_exists = User.get_or_none(User.username == field.data)
    if username_exists:
        raise ValidationError(_('The username is already in use'))


def UniqueEmailRequired(__: 'RegisterForm', field: StringField) -> None:
    email_exists = User.get_or_none(User.mail_address == field.data)
    if email_exists:
        raise ValidationError(_('The email is already in use'))


def EmailNotExists(__: 'ResetPassForm', field: StringField) -> None:
    email_exists = User.get_or_none(User.mail_address == field.data)
    if not email_exists:
        raise ValidationError(_('Invalid email'))
