import enum
import os
import secrets
from urllib.parse import urljoin, urlparse

import flask
from flask import Flask, render_template, request, session, url_for

from flask_admin import Admin, AdminIndexView  # type: ignore
from flask_admin.contrib.peewee import ModelView  # type: ignore

from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)

from peewee import (  # type: ignore
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    ManyToManyField,
    Model,
    PostgresqlDatabase,
    SqliteDatabase,
)

from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import redirect

webapp = Flask(__name__)
webapp.config.from_pyfile('config.py')

login_manager = LoginManager()
login_manager.init_app(webapp)
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'

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


@webapp.before_first_request
def before_first_request():
    session['csrf'] = session.get('csrf', secrets.token_urlsafe(32))


@webapp.after_request
def after_request(response):
    for name, value in PERMISSIVE_CORS.items():
        response.headers.add(name, value)
    return response


@login_manager.user_loader
def load_user(user_id):
    return User.get_or_none(id=user_id)


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return (
            test_url.scheme in ('http', 'https')
            and ref_url.netloc == test_url.netloc
    )


@webapp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main'))

    username = request.form.get('username')
    password = request.form.get('password')
    user = User.get_or_none(username=username)

    if user is not None and user.is_password_valid(password):
        login_user(user)
        next_url = request.args.get('next_url')
        if not is_safe_url(next_url):
            return flask.abort(400)
        return redirect(next_url or url_for('main'))

    return render_template('login.html')


@webapp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('login')


@webapp.route('/')
@login_required
def main():
    return render_template('exercises.html', csrf_token=session['csrf'])


@webapp.route('/send')
@login_required
def send():
    return render_template('upload.html')


@webapp.route('/upload', methods=['POST'])
def upload():
    # TODO: Save the files WITHOUT EXECUTION PERMISSIONS
    # TODO: Check that the file is ipynb/py
    # TODO: Extract the right exercise from the notebook
    #       (ask Efrat for code)
    # TODO: Check max filesize of (max notebook size + 20%)
    return 'yay'


@webapp.route('/view')
def view():
    return render_template('view.html')


class RoleOptions(enum.Enum):
    STUDENT_ROLE = 'Student'
    STAFF_ROLE = 'Staff'
    ADMINISTRATOR_ROLE = 'Administrator'


if webapp.debug:
    database = SqliteDatabase('db.sqlite')
elif webapp.env == 'production':
    db_config = {
        'database': webapp.config['DB_NAME'],
        'user': webapp.config['DB_USER'],
        'port': webapp.config['DB_PORT'],
        'host': webapp.config['DB_HOST_IP'],
        'password': webapp.config['DB_PASSWORD'],
    }
    database = PostgresqlDatabase(**db_config)


class BaseModel(Model):
    class Meta:
        database = database


class Role(BaseModel):
    name = CharField(unique=True, choices=(
        (RoleOptions.ADMINISTRATOR_ROLE.value,
         RoleOptions.ADMINISTRATOR_ROLE.value),
        (RoleOptions.STAFF_ROLE.value, RoleOptions.STAFF_ROLE.value),
        (RoleOptions.STUDENT_ROLE.value, RoleOptions.STUDENT_ROLE.value),
    ))

    def __str__(self):
        return self.name

    @property
    def is_student(self):
        return self.name == RoleOptions.STUDENT_ROLE.value

    @property
    def is_staff(self):
        return self.name == RoleOptions.STAFF_ROLE.value

    @property
    def is_administrator(self):
        return self.name == RoleOptions.ADMINISTRATOR_ROLE.value


class User(UserMixin, BaseModel):
    username = CharField(unique=True)
    fullname = CharField()
    mail_address = CharField()
    saltedhash = CharField()
    role = ForeignKeyField(Role, backref='users')

    def set_password(self, password):
        self.saltedhash = generate_password_hash(password)
        self.save()

    def is_password_valid(self, password):
        return check_password_hash(self.saltedhash, password)

    def __str__(self):
        return f'{self.username} - {self.fullname}'


class Exercise(BaseModel):
    subject = CharField()
    date = DateTimeField()
    users = ManyToManyField(User, backref='exercises')
    is_archived = BooleanField()

    def __str__(self):
        return self.subject


StudentLecture = Exercise.users.get_through_model()

ALL_MODELS = (User, Exercise, Role, StudentLecture)


class AccessibleByAdminMixin:
    def is_accessible(self):
        return (
                current_user.is_authenticated
                and current_user.role.is_administrator
        )


class MyAdminIndexView(AccessibleByAdminMixin, AdminIndexView):
    pass


class AdminModelView(AccessibleByAdminMixin, ModelView):
    pass


admin = Admin(
    webapp,
    name='LMS',
    template_mode='bootstrap3',
    index_view=MyAdminIndexView(),
)

for m in ALL_MODELS:
    admin.add_view(AdminModelView(m))

if __name__ == '__main__':
    is_prod = os.getenv('env', '').lower() == 'production'
    APP_CONFIG['port'] = 443 if is_prod else 80
    APP_CONFIG['debug'] = not is_prod
    webapp.run(**APP_CONFIG)  # type: ignore
