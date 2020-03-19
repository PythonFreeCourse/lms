import os
import secrets


from flask import Flask, render_template, session

webapp = Flask(__name__)
webapp.config.from_pyfile('config.py')

PERMISSIVE_CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,PUT,POST,DELETE',
}


APP_CONFIG = {
    'host': '0.0.0.0',  # NOQA
    'port': 80,
    'debug': webapp.debug,
    'threaded': True,
}


@webapp.route('/')
def main():
    # TODO: If logged in exercises page
    return render_template('login.html', csrf_token=session['csrf'])


@webapp.before_first_request
def before_first_request():
    session['csrf'] = session.get('csrf', secrets.token_urlsafe(32))


@webapp.after_request
def after_request(response):
    for name, value in PERMISSIVE_CORS.items():
        response.headers.add(name, value)
    return response


if __name__ == '__main__':
    is_prod = os.getenv('env', '').lower() == 'production'
    APP_CONFIG['port'] = 443 if is_prod else 80
    APP_CONFIG['debug'] = not is_prod
    webapp.run(**APP_CONFIG)  # type: ignore
