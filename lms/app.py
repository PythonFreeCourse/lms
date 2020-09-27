from typing import Any, Dict

from lms.lmsweb import webapp

if __name__ == '__main__':
    APP_CONFIG: Dict[str, Any] = {
        'port': 8080,
    }

    webapp.run(**APP_CONFIG)
