import enum
import secrets
import string

from flask_admin import Admin, AdminIndexView  # type: ignore
from flask_admin.contrib.peewee import ModelView  # type: ignore
from flask_login import (UserMixin, current_user)
from lms.lmsweb import webapp
from peewee import (  # type: ignore
    BooleanField,
    CharField,
    Check,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    ManyToManyField,
    PostgresqlDatabase,
    SqliteDatabase,
    TextField,
)
from playhouse.signals import Model, pre_save
from playhouse.shortcuts import model_to_dict
from werkzeug.security import check_password_hash, generate_password_hash


class RoleOptions(enum.Enum):
    STUDENT = 'Student'
    STAFF = 'Staff'
    ADMINISTRATOR = 'Administrator'

    def __str__(self):
        return self.value


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
        (RoleOptions.ADMINISTRATOR.value,
         RoleOptions.ADMINISTRATOR.value),
        (RoleOptions.STAFF.value, RoleOptions.STAFF.value),
        (RoleOptions.STUDENT.value, RoleOptions.STUDENT.value),
    ))

    def __str__(self):
        return self.name

    @property
    def is_student(self):
        return self.name == RoleOptions.STUDENT.value

    @property
    def is_staff(self):
        return self.name == RoleOptions.STAFF.value

    @property
    def is_administrator(self):
        return self.name == RoleOptions.ADMINISTRATOR.value


class User(UserMixin, BaseModel):
    username = CharField(unique=True)
    fullname = CharField()
    mail_address = CharField(unique=True)
    password = CharField()
    role = ForeignKeyField(Role, backref='users')

    def is_password_valid(self, password):
        return check_password_hash(self.password, password)

    def __str__(self):
        return f'{self.username} - {self.fullname}'


@pre_save(sender=User)
def on_save_handler(model_class, instance, created):
    if created:
        instance.password = generate_password_hash(instance.password)


class Exercise(BaseModel):
    subject = CharField()
    date = DateTimeField()
    users = ManyToManyField(User, backref='exercises')
    is_archived = BooleanField()

    def __str__(self):
        return self.subject


class Solution(BaseModel):
    exercise = ForeignKeyField(Exercise, backref='solutions')
    solver = ForeignKeyField(User, backref='solutions')
    checker = ForeignKeyField(User, null=True, backref='solutions')
    is_checked = BooleanField(default=False)
    grade = IntegerField(
        default=0, constraints=[Check('grade <= 100'), Check('grade >= 0')]
    )
    submission_timestamp = DateTimeField()
    json_data_str = TextField()


class CommentText(BaseModel):
    text = TextField(unique=True)


class Comments(BaseModel):
    commenter = ForeignKeyField(User, backref='comments')
    timestamp = DateTimeField()
    line_number = IntegerField(constraints=[Check('line_number >= 1')])
    comment = ForeignKeyField(CommentText)
    solution = ForeignKeyField(Solution)


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

ALL_MODELS = (User, Exercise, CommentText, Solution, Role, Comments)
for m in ALL_MODELS:
    admin.add_view(AdminModelView(m))

database.create_tables(ALL_MODELS, safe=True)


def generate_password():
    randomizer = secrets.SystemRandom()
    length = randomizer.randrange(9, 16)
    password = randomizer.choices(string.printable[:66], k=length)
    return ''.join(password)


if Role.select().count() == 0:
    for role in RoleOptions:
        Role.create(name=role.value)

if User.select().count() == 0:
    password = generate_password()
    User.create(
        username='lmsadmin',
        fullname='LMS Admin',
        password=password,
        mail_address='lms@pythonic.guru',
        role=Role.get(name=RoleOptions.ADMINISTRATOR.value),
    )
    print(f"First run! Your login is lmsadmin:{password}")
