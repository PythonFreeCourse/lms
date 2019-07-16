import os

from flask import Flask

PERMISSIVE_CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,PUT,POST,DELETE',
}


def create_app():
    return Flask(__name__)


app = create_app()


@app.after_request
def after_request(response):
    for name, value in PERMISSIVE_CORS.items():
        response.headers.add(name, value)
    return response


if __name__ == '__main__':
    APP_CONFIG = {
        'host': '0.0.0.0',
        'port': 80,
        'debug': app.debug,
        'threaded': True,
    }

    is_prod = os.getenv('env', '').lower() == 'prod'
    APP_CONFIG['port'] = 443 if is_prod else 80
    APP_CONFIG['debug'] = not is_prod

    app.run(host='0.0.0.0', port=80, debug=app.debug, threaded=True)
