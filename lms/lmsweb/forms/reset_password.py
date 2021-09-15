from lms.lmsweb.tools.validators import EmailNotExists
from flask_babel import gettext as _  # type: ignore
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.fields.simple import PasswordField
from wtforms.validators import Email, EqualTo, InputRequired, Length


class ResetPassForm(FlaskForm):
    email = StringField(
        'Email', validators=[
            InputRequired(), Email(message=_('אימייל לא תקין')),
            EmailNotExists,
        ],
    )


class RecoverPassForm(FlaskForm):
    password = PasswordField(
        'Password', validators=[InputRequired(), Length(min=8)], id='password',
    )
    confirm = PasswordField(
        'Password Confirmation', validators=[
            InputRequired(),
            EqualTo('password', message=_('הסיסמאות שהוקלדו אינן זהות')),
        ],
    )
