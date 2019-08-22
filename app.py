import os

# Importing `models` to have it initialized.
from lmsweb import app, models  # NOQA: F401

APP_CONFIG = {
    'host': '0.0.0.0',  # NOQA
    'port': 80,
    'debug': app.debug,
    'threaded': True,
}

if __name__ == '__main__':
    is_prod = os.getenv('env').lower() == 'production'
    APP_CONFIG['port'] = 443 if is_prod else 80
    APP_CONFIG['debug'] = not is_prod
    app.run(**APP_CONFIG)  # type: ignore
