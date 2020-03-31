import pathlib

from flask import Flask
from flask_wtf.csrf import CSRFProtect  # type: ignore

project_dir = pathlib.Path(__file__).resolve().parent.parent
template_dir = str(project_dir / 'templates')
static_dir = str(project_dir / 'static')

webapp = Flask(
    __name__,
    template_folder=template_dir,
    static_folder=static_dir,
)

webapp.config.from_pyfile('config.py')

csrf = CSRFProtect(webapp)

# Must import files after app's creation
from lms.lmsdb import models  # NOQA: F401
from lms.lmsweb import views  # NOQA: F401


# gunicorn search for application
application = webapp
