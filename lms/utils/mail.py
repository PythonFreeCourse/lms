from functools import wraps

from flask import url_for
from flask_babel import gettext as _  # type: ignore
from flask_mail import Message  # type: ignore

from lms.lmsdb.models import User
from lms.lmsweb import config, webapp, webmail
from lms.models.users import generate_user_token


def send_message(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        msg = func(*args, **kwargs)
        if not webapp.config.get('DISABLE_MAIL'):
            webmail.send(msg)

    return wrapper


@send_message
def send_confirmation_mail(user: User) -> Message:
    token = generate_user_token(user)
    subject = _(
        'Confirmation mail - %(site_name)s', site_name=config.SITE_NAME,
    )
    msg = Message(subject, recipients=[user.mail_address])
    link = url_for(
        'confirm_email', user_id=user.id, token=token, _external=True,
    )
    msg.body = _(
        'Hello %(fullname)s,\nYour confirmation link is: %(link)s',
        fullname=user.fullname, link=link,
    )
    return msg


@send_message
def send_reset_password_mail(user: User) -> Message:
    token = generate_user_token(user)
    subject = _(
        'Reset password mail - %(site_name)s', site_name=config.SITE_NAME,
    )
    msg = Message(subject, recipients=[user.mail_address])
    link = url_for(
        'recover_password', user_id=user.id, token=token, _external=True,
    )
    msg.body = _(
        'Hello %(fullname)s,\nYour reset password link is: %(link)s',
        fullname=user.fullname, link=link,
    )
    return msg


@send_message
def send_change_password_mail(user: User) -> Message:
    subject = _(
        'Changing password - %(site_name)s', site_name=config.SITE_NAME,
    )
    msg = Message(subject, recipients=[user.mail_address])
    msg.body = _(
        'Hello %(fullname)s. Your password in %(site_name)s site has been '
        "changed.\nIf you didn't do it please contact with the site "
        'management.\nMail address: %(site_mail)s',
        fullname=user.fullname, site_name=config.SITE_NAME,
        site_mail=config.MAIL_DEFAULT_SENDER,
    )
    return msg
