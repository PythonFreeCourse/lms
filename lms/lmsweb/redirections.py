from typing import Optional
from urllib.parse import urljoin, urlparse

from flask import request, url_for
from flask_login import LoginManager
from werkzeug.utils import redirect

from lms.lmsweb import webapp
from lms.models.errors import fail


login_manager = LoginManager()
login_manager.init_app(webapp)
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'

PERMISSIVE_CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,PUT,POST,DELETE',
}

MAX_REQUEST_SIZE = 2_000_000  # 2MB (in bytes)


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return (
        test_url.scheme in ('http', 'https')
        and ref_url.netloc == test_url.netloc
    )


def get_next_url(url_next_param: Optional[str]):
    next_url = url_next_param if url_next_param else None
    if not is_safe_url(next_url):
        return fail(400, "The URL isn't safe.")
    return redirect(next_url or url_for('main'))
