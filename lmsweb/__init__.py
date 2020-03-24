import os

from flask import Flask
from flask_wtf.csrf import CSRFProtect  # type: ignore

project_dir = os.path.abspath(os.path.curdir)
template_dir = os.path.join(project_dir, 'templates')
static_dir = os.path.join(project_dir, 'static')
webapp = Flask(
    __name__,
    template_folder=template_dir,
    static_folder=static_dir,
)
webapp.config.from_pyfile('config.py')

csrf = CSRFProtect(webapp)

# Must import files after app's creation
from lms.lmsweb import models, views  # NOQA: F401
