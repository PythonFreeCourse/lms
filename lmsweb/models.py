import enum
import secrets
import string
from datetime import datetime

from flask_admin import Admin, AdminIndexView  # type: ignore
from flask_admin.contrib.peewee import ModelView  # type: ignore
from flask_login import UserMixin, current_user  # type: ignore
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
from playhouse.signals import Model, pre_save  # type: ignore
from werkzeug.security import check_password_hash, generate_password_hash

from lms.lmsweb import webapp


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
        'autorollback': webapp.config['DB_AUTOROLLBACK'],
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

    @classmethod
    def get_student_role(cls):
        return cls.get(**{
            Role.name.name: RoleOptions.STUDENT.value
        })

    @classmethod
    def by_name(cls, name):
        if name.startswith('_'):
            raise ValueError("That could lead to a security issue.")
        role_name = getattr(RoleOptions, name.upper()).value
        return cls.get(name=role_name)

    @property
    def is_student(self):
        return self.name == RoleOptions.STUDENT.value

    @property
    def is_staff(self):
        return self.name == RoleOptions.STAFF.value

    @property
    def is_administrator(self):
        return self.name == RoleOptions.ADMINISTRATOR.value

    @property
    def is_manager(self):
        return self.is_staff or self.is_administrator


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
    """Hashes password on creation/save"""

    # If password changed then it won't start with hash's method prefix
    is_password_changed = not instance.password.startswith('pbkdf2:sha256')
    if created or is_password_changed:
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
        default=0, constraints=[Check('grade <= 100'), Check('grade >= 0')],
    )
    submission_timestamp = DateTimeField()
    json_data_str = TextField()

    @classmethod
    def next_unchecked(cls):
        unchecked_exercises = cls.select().where(cls.is_checked == False)  # NOQA: E712, E501
        try:
            return unchecked_exercises.dicts().get()
        except cls.DoesNotExist:
            return {}

    @classmethod
    def next_unchecked_of(cls, exercise_id):
        try:
            return cls.select().where(
                (cls.is_checked == 0) & (exercise_id == cls.exercise)
            ).dicts().get()
        except cls.DoesNotExist:
            return {}


class CommentText(BaseModel):
    text = TextField(unique=True)


class Comment(BaseModel):
    commenter = ForeignKeyField(User, backref='comments')
    timestamp = DateTimeField(default=datetime.now)
    line_number = IntegerField(constraints=[Check('line_number >= 1')])
    comment = ForeignKeyField(CommentText)
    solution = ForeignKeyField(Solution)

    @classmethod
    def by_solution(cls, solution_id: int):
        return tuple((
            Comment
            .select(Comment, CommentText.text)
            .join(CommentText)
            .where(Comment.solution == solution_id)
        ).dicts())


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


def generate_password():
    randomizer = secrets.SystemRandom()
    length = randomizer.randrange(9, 16)
    password = randomizer.choices(string.printable[:66], k=length)
    return ''.join(password)


def create_demo_users():
    print("First run! Here are some users to get start with:")
    fields = ['username', 'fullname', 'mail_address', 'role']
    student_role = Role.by_name('Student')
    admin_role = Role.by_name('Administrator')
    entities = [
        ['lmsadmin', 'Admin', 'lms@pythonic.guru', admin_role],
        ['user', 'Student', 'student@pythonic.guru', student_role],
    ]

    for entity in entities:
        user = dict(zip(fields, entity))
        password = generate_password()
        User.create(**user, password=password)
        print(f"User: {user['username']}, Password: {password}")


def create_basic_roles():
    for role in RoleOptions:
        Role.create(name=role.value)


with database.connection_context():
    admin = Admin(
        webapp,
        name='LMS',
        template_mode='bootstrap3',
        index_view=MyAdminIndexView(),
    )

    ALL_MODELS = (User, Exercise, CommentText, Solution, Role, Comment)
    for m in ALL_MODELS:
        admin.add_view(AdminModelView(m))

    database.create_tables(ALL_MODELS, safe=True)

    if Role.select().count() == 0:
        create_basic_roles()
    if User.select().count() == 0:
        create_demo_users()
