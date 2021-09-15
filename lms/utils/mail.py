from flask import url_for
from flask_babel import gettext as _  # type: ignore
from flask_mail import Message  # type: ignore

from lms.lmsdb.models import User
from lms.lmsweb import config, webapp, webmail
from lms.models.users import generate_confirmation_token


def send_confirmation_mail(user: User) -> None:
    token = generate_confirmation_token(user)
    subject = _('מייל אימות - %(site_name)s', site_name=config.SITE_NAME)
    msg = Message(subject, recipients=[user.mail_address])
    link = url_for(
        'confirm_email', user_id=user.id, token=token, _external=True,
    )
    msg.body = _(
        'שלום %(fullname)s,\nלינק האימות שלך למערכת הוא: %(link)s',
        fullname=user.fullname, link=link,
    )
    if not webapp.config.get('TESTING'):
        webmail.send(msg)


def send_change_password_mail(user: User) -> None:
    subject = _('שינוי סיסמה - %(site_name)s', site_name=config.SITE_NAME)
    msg = Message(subject, recipients=[user.mail_address])
    msg.body = _(
        'שלום %(fullname)s. הסיסמה שלך באתר %(site_name)s שונתה.\n'
        'אם אתה לא עשית את זה צור קשר עם הנהלת האתר.\n'
        'כתובת המייל: %(site_mail)s',
        fullname=user.fullname, site_name=config.SITE_NAME,
        site_mail=config.MAIL_DEFAULT_SENDER,
    )
    if not webapp.config.get('TESTING'):
        webmail.send(msg)
