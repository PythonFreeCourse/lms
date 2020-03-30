from typing import Any, Dict

from lmsweb import webapp

if __name__ == '__main__':
    APP_CONFIG: Dict[str, Any] = {}

    webapp.run(**APP_CONFIG)
