from flask_babel import gettext as _  # type: ignore
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import Email, EqualTo, InputRequired, Length

from lms.lmsweb.tools.validators import (
    UniqueEmailRequired, UniqueUsernameRequired,
)


class RegisterForm(FlaskForm):
    email = StringField(
        'Email', validators=[
            InputRequired(), Email(message=_('אימייל לא תקין')),
            UniqueEmailRequired,
        ],
    )
    username = StringField(
        'Username', validators=[
            InputRequired(), UniqueUsernameRequired, Length(min=4, max=20),
        ],
    )
    fullname = StringField(
        'Full Name', validators=[InputRequired(), Length(min=3, max=60)],
    )
    password = PasswordField(
        'Password', validators=[InputRequired(), Length(min=8)], id='password',
    )
    confirm = PasswordField(
        'Password Confirmation', validators=[
            InputRequired(),
            EqualTo('password', message=_('הסיסמאות שהוקלדו אינן זהות')),
        ],
    )
