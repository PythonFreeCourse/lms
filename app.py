import os

from lms.lmsweb import webapp

if __name__ == '__main__':
    APP_CONFIG = {
        'host': '0.0.0.0',  # NOQA
        'port': 80,
        'threaded': True,
    }

    is_prod = os.getenv('env', '').lower() == 'production'
    APP_CONFIG['port'] = 443 if is_prod else 80
    webapp.run(**APP_CONFIG)
