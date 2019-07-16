import os

from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.peewee import ModelView
from app.models import User, database, Course

app = Flask(__name__)
app.secret_key = 'fake secret key'

# set optional bootswatch theme
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'

admin = Admin(app, name='LMS', template_mode='bootstrap3')
admin.add_view(ModelView(User))
admin.add_view(ModelView(Course))

PERMISSIVE_CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,PUT,POST,DELETE',
}


@app.after_request
def after_request(response):
    for name, value in PERMISSIVE_CORS.items():
        response.headers.add(name, value)
    return response


@app.route('/')
def t():
    return 'hi'


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

    app.run(**APP_CONFIG)
