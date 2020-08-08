import pathlib
import shutil

from flask import Flask
from flask_wtf.csrf import CSRFProtect  # type: ignore

project_dir = pathlib.Path(__file__).resolve().parent.parent
web_dir = project_dir / 'lmsweb'
template_dir = project_dir / 'templates'
static_dir = project_dir / 'static'
config_file = web_dir / 'config.py'


webapp = Flask(
    __name__,
    template_folder=str(template_dir),
    static_folder=str(static_dir),
)


if not config_file.exists():
    shutil.copy(str(web_dir / 'config.py.example'), str(config_file))
webapp.config.from_pyfile(str(config_file))

csrf = CSRFProtect(webapp)

# Must import files after app's creation
from lms.lmsdb import models  # NOQA: F401, E402
from lms.lmsweb import views  # NOQA: F401, E402


# gunicorn search for application
application = webapp
