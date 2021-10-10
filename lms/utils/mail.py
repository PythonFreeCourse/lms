from functools import wraps
from typing import Iterable

from flask import url_for
from flask_babel import gettext as _  # type: ignore
from flask_babel import ngettext  # type: ignore
from flask_mail import Message  # type: ignore

from lms.lmsdb.models import MailMessage, User
from lms.lmsweb import config, webapp, webmail, webscheduler
from lms.models.users import generate_user_token
from lms.utils.config.celery import app


@app.task
def send_message(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with webapp.app_context():
            msg = func(*args, **kwargs)
            if not webapp.config.get('DISABLE_MAIL'):
                return webmail.send(msg)

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


@send_message
def send_notification_mail(user_id: int, message: str, number: int) -> Message:
    user = User.get_by_id(user_id)
    subject = _(
        'New notification - %(site_name)s', site_name=config.SITE_NAME,
    )
    msg = Message(subject, recipients=[user.mail_address])
    msg.body = ngettext(
        'Hello %(fullname)s. You have %(num)d '
        'new notification:\n%(message)s',
        'Hello %(fullname)s. You have %(num)d '
        'new notifications:\n%(message)s',
        fullname=user.fullname, num=number, message=message,
    )
    return msg


def build_notification_message(mails: Iterable[MailMessage]) -> str:
    return '\n'.join(mail.notification.message.strip() for mail in mails)


@webscheduler.task(
    'interval', id='mail_notifications',
    hours=config.DEFAULT_DO_TASKS_EVERY_HOURS,
)
def send_all_notifications_mails():
    for mail_message_user in MailMessage.distincit_users():
        mails = MailMessage.by_user(mail_message_user.user)
        message = build_notification_message(mails)

        if mail_message_user.user.mail_subscription:
            send_message(send_notification_mail(
                mail_message_user.user.id, message,
                MailMessage.user_messages_number(mail_message_user.user.id),
            ))
        MailMessage.delete().where(
            MailMessage.user == mail_message_user.user,
        ).execute()
