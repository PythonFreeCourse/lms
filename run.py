import os

from lmsweb import app

APP_CONFIG = {
    'host': '0.0.0.0', # NOQA
    'port': 80,
    'debug': app.debug,
    'threaded': True,
}

is_prod = os.getenv('env', '').lower() == 'prod'
APP_CONFIG['port'] = 443 if is_prod else 80
APP_CONFIG['debug'] = not is_prod
app.run(**APP_CONFIG)
