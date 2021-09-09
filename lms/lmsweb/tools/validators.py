from flask_babel import gettext as _  # type: ignore
from wtforms.validators import ValidationError

from lms.lmsdb.models import User


def UniqueUsernameRequired(form, field):
    username_exists = User.get_or_none(User.username == field.data)
    if username_exists:
        raise ValidationError(_('שם המשתמש כבר נמצא בשימוש'))


def UniqueEmailRequired(form, field):
    email_exists = User.get_or_none(User.mail_address == field.data)
    if email_exists:
        raise ValidationError(_('האימייל כבר נמצא בשימוש'))
