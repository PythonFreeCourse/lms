import re

from flask import url_for
from flask_babel import gettext as _  # type: ignore
from flask_mail import Message  # type: ignore
from itsdangerous import URLSafeTimedSerializer

from lms.lmsdb.models import User
from lms.lmsweb import config, webapp, webmail
from lms.models.errors import EmptyPasswordError, UnhashedPasswordError


SERIALIZER = URLSafeTimedSerializer(config.SECRET_KEY)


def retrieve_salt(user: User) -> str:
    try:
        re.findall(r'\$(.*)\$', user.password)[0]
    except IndexError:
        if user.password.name:
            raise UnhashedPasswordError
        raise EmptyPasswordError


def generate_confirmation_token(user: User) -> str:
    return SERIALIZER.dumps(user.mail_address, salt=retrieve_salt(user))


def send_confirmation_mail(user: User) -> None:
    token = generate_confirmation_token(user)
    subject = _('מייל אימות - %(site_name)s', site_name=config.SITE_NAME)
    msg = Message(
        subject, sender=f'lms@{config.MAILGUN_DOMAIN}',
        recipients=[user.mail_address],
    )
    link = url_for(
        'confirm_email', user_id=user.id, token=token, _external=True,
    )
    msg.body = _(
        'שלום %(fullname)s,\nלינק האימות שלך למערכת הוא: %(link)s',
        fullname=user.fullname, link=link,
    )
    if not webapp.config.get('TESTING'):
        webmail.send(msg)
