import pathlib
import shutil
import typing

from flask import Flask
from flask_babel import Babel  # type: ignore
from flask_httpauth import HTTPBasicAuth
from flask_limiter import Limiter  # type: ignore
from flask_limiter.util import get_remote_address  # type: ignore
from flask_mail import Mail  # type: ignore
from flask_wtf.csrf import CSRFProtect  # type: ignore

from lms.utils import config_migrator, debug

project_dir = pathlib.Path(__file__).resolve().parent.parent
web_dir = project_dir / 'lmsweb'
template_dir = project_dir / 'templates'
static_dir = project_dir / 'static'
config_file = web_dir / 'config.py'
config_example_file = web_dir / 'config.py.example'


if debug.is_enabled():
    debug.start()


webapp = Flask(
    __name__,
    template_folder=str(template_dir),
    static_folder=str(static_dir),
)

http_basic_auth = HTTPBasicAuth()

limiter = Limiter(webapp, key_func=get_remote_address)


if not config_file.exists():
    shutil.copy(str(config_example_file), str(config_file))
config_migrator.migrate(config_file, config_example_file)

webapp.config.from_pyfile(str(config_file))

csrf = CSRFProtect(webapp)

# Localizing configurations
babel = Babel(webapp)

webmail = Mail(webapp)


# Must import files after app's creation
from lms.lmsdb import models  # NOQA: F401, E402, I202
from lms.lmsweb import views  # NOQA: F401, E402


# gunicorn search for application
application = webapp


@http_basic_auth.get_password
def get_password(username: str) -> typing.Optional[str]:
    user = models.User.get_or_none(models.User.username == username)
    return user.password if user else None


@http_basic_auth.verify_password
def verify_password(username: str, client_password: str):
    username_username = models.User.username == username
    login_user = models.User.get_or_none(username_username)
    if login_user is None or not login_user.is_password_valid(client_password):
        return False
    return login_user
