from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.fields.simple import PasswordField
from wtforms.validators import InputRequired, Length


class LoginForm(FlaskForm):
    username = StringField(
        'Username', validators=[
            InputRequired(), Length(min=4, max=20),
        ],
    )
    password = PasswordField(
        'Password', validators=[InputRequired(), Length(min=8)], id='password',
    )
