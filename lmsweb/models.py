import enum
import os

from flask_admin import Admin  # type: ignore
from flask_admin.contrib.peewee import ModelView  # type: ignore

from lms.app import webapp

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


class RoleOptions(enum.Enum):
    STUDENT_ROLE = 'Student'
    STAFF_ROLE = 'Staff'
    ADMINISTRATOR_ROLE = 'Administrator'


if webapp.debug:
    database = SqliteDatabase(os.path.join(webapp.instance_path, 'db.sqlite'))
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


class User(BaseModel):
    username = CharField(unique=True)
    fullname = CharField()
    mail_address = CharField()
    password = CharField()
    saltedhash = CharField()
    role = ForeignKeyField(Role, backref='users')

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

admin = Admin(webapp, name='LMS', template_mode='bootstrap3')

for m in ALL_MODELS:
    admin.add_view(ModelView(m))
