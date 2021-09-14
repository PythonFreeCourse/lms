from flask_babel import gettext as _  # type: ignore
from flask_wtf import FlaskForm
from wtforms import PasswordField
from wtforms.validators import EqualTo, InputRequired, Length, ValidationError


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        'Password', validators=[InputRequired(), Length(min=8)], id='password',
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

    def __init__(self, user, *args, **kwargs):
        super(ChangePasswordForm, self).__init__(*args, **kwargs)
        self.user = user

    def validate_current_password(self, field):
        if not self.user.is_password_valid(field.data):
            raise ValidationError(_('הסיסמה הנוכחית שהוזנה שגויה'))
