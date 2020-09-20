import ast
import pathlib
import shutil
from typing import Any, Dict, Optional, Set, Tuple

from flask import Flask
from flask_babel import Babel
from flask_wtf.csrf import CSRFProtect  # type: ignore

project_dir = pathlib.Path(__file__).resolve().parent.parent
web_dir = project_dir / 'lmsweb'
template_dir = project_dir / 'templates'
static_dir = project_dir / 'static'
config_file = web_dir / 'config.py'
config_example_file = web_dir / 'config.py.example'


def next_dict_key(d: Dict[Any, Any], key: Any) -> Optional[Any]:
    dict_iter = iter(d)
    for k in dict_iter:
        if k == key:
            return next(dict_iter, None)
    return None


def open_file(path: str) -> str:
    with open(path) as file:
        return file.read()


def get_configs_values() -> Tuple[Set[str], Dict[str, int]]:
    config_values = {
        x.id for x in ast.walk(
            ast.parse(open_file(str(config_file))),
        )
        if isinstance(x, ast.Name) and x.col_offset == 0
    }
    config_example_values = {
        x.id: x.lineno for x in ast.walk(
            ast.parse(open_file(str(config_example_file))),
        )
        if isinstance(x, ast.Name) and x.col_offset == 0
    }
    return config_values, config_example_values


def config_migrator() -> None:
    config_values, config_example_values = get_configs_values()
    missing_values = set(config_example_values).difference(config_values)

    example_lines = open_file(str(config_example_file)).splitlines()

    with open(str(config_file), 'a') as main_config:
        for missing_value in missing_values:
            starting_line = config_example_values[missing_value] - 1
            next_value = next_dict_key(config_example_values, missing_value)
            if next_value is not None:
                ending_line = config_example_values[next_value] - 1
                for line in example_lines[starting_line:ending_line]:
                    main_config.write(line + '\n')
            else:
                for line in example_lines[starting_line:]:
                    main_config.write(line + '\n')


webapp = Flask(
    __name__,
    template_folder=str(template_dir),
    static_folder=str(static_dir),
)


if not config_file.exists():
    shutil.copy(str(config_example_file), str(config_file))
config_migrator()

webapp.config.from_pyfile(str(config_file))

csrf = CSRFProtect(webapp)

# Localizing configurations
babel = Babel(webapp)

# Must import files after app's creation
from lms.lmsdb import models  # NOQA: F401, E402
from lms.lmsweb import views  # NOQA: F401, E402


# gunicorn search for application
application = webapp
