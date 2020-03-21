import enum

from flask_admin import Admin, AdminIndexView  # type: ignore
from flask_admin.contrib.peewee import ModelView  # type: ignore
from flask_login import (UserMixin, current_user)
from peewee import (  # type: ignore
    BooleanField,
    CharField,
    Check,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    ManyToManyField,
    Model,
    PostgresqlDatabase,
    SqliteDatabase,
    TextField,
)
from werkzeug.security import check_password_hash, generate_password_hash

from lms.lmsweb import webapp


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
        # TODO: Make this work in admin form? Seems like it works for
        #  sqlalchemy...
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


class Solution(BaseModel):
    exercise = ForeignKeyField(Exercise, backref='solutions')
    solver = ForeignKeyField(User, backref='solutions')
    checker = ForeignKeyField(User, backref='solutions')
    is_checked = BooleanField(default=False)
    grade = IntegerField(
        default=0, constraints=[Check('grade <= 100'), Check('grade >= 0')]
    )
    submission_timestamp = DateTimeField()


class Comment(BaseModel):
    commenter = ForeignKeyField(User, backref='comments')
    timestamp = DateTimeField()
    exercise = ForeignKeyField(Exercise, backref='comments')
    comment_text = TextField()
    line_number = IntegerField(constraints=[Check('line_number >= 1')])


class CommentsToSolutions(BaseModel):
    comment = ForeignKeyField(Comment)
    solution = ForeignKeyField(Solution)


class AccessibleByAdminMixin:
    def is_accessible(self):
        return (
                current_user.is_authenticated
                and current_user.role.is_administrator
        )


class MyAdminIndexView(AccessibleByAdminMixin, AdminIndexView):
    pass


ALL_MODELS = (User, Exercise, Comment, Solution, Role)


class AdminModelView(AccessibleByAdminMixin, ModelView):
    pass


admin = Admin(
        webapp,
        name='LMS',
        template_mode='bootstrap3',
        index_view=MyAdminIndexView(),
)

for m in (User, Role, Exercise):
    admin.add_view(AdminModelView(m))

database.create_tables(ALL_MODELS, safe=True)
