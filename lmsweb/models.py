from flask_admin import Admin
from flask_admin.contrib.peewee import ModelView

from lmsweb import app

from peewee import (
    CharField,
    DateTimeField,
    ForeignKeyField,
    Model,
    PostgresqlDatabase,
    BooleanField)

STUDENT_ROLE = 'Student'
STAFF_ROLE = 'Staff'
ADMINISTRATOR_ROLE = 'Administrator'

db_config = {
    'database': app.config['DB_NAME'],
    'user': app.config['USER'],
    'port': app.config['PORT'],
    'host': app.config['HOST_IP'],
    'password': app.config['PASSWORD'],
}
database = PostgresqlDatabase(**db_config)


# Database models
class BaseModel(Model):
    class Meta:
        database = database


class Course(BaseModel):
    name = CharField()
    open_date = DateTimeField()


class Role(BaseModel):
    name = CharField(unique=True, choices=(
        (ADMINISTRATOR_ROLE, ADMINISTRATOR_ROLE),
        (STAFF_ROLE, STAFF_ROLE),
        (STUDENT_ROLE, STUDENT_ROLE),
    ))


class User(BaseModel):
    username = CharField(unique=True)
    fullname = CharField()
    mail_address = CharField()
    password = CharField()
    role = ForeignKeyField(Role, backref='users')
    is_administrator = BooleanField(default=False)
    course = ForeignKeyField(Course, backref='users', null=True)


class Lecture(BaseModel):
    course = ForeignKeyField(Course, backref='lectures')
    date = DateTimeField()
    subject = CharField()


ALL_MODELS = (User, Course, Lecture, Role)

admin = Admin(app, name='LMS', template_mode='bootstrap3')

for m in ALL_MODELS:
    admin.add_view(ModelView(m))


def create_tables():
    with database:
        database.create_tables(ALL_MODELS)


def test():
    database.drop_tables(
        [
            User,
            Course,
            Lecture,
            UserCourseRelationship,
            UserLectureRelationship,
        ],
    )
    create_tables()
    from datetime import date

    today = date.today()
    add_course(course_id=1111, name='course1', open_date=today)
    add_course(course_id=1112, name='course2', open_date=today)
    add_course(course_id=1113, name='course3', open_date=today)
    add_course(course_id=1114, name='course4', open_date=today)
    add_user(  # NOQA: S106
        username='user1',
        fullname='User User',
        mail_address='user@user.com',
        password='somehash',
        user_type='admin',
    )
    user2 = add_user(  # NOQA: S106, F841
        username='user2',
        fullname='User2 User2',
        mail_address='user2@user2.com',
        password='somehash2',
        user_type='student',
    )

    add_lecture(lecture_id=992, course_id=1111, date=today, subject='lecture2')
    add_lecture(lecture_id=993, course_id=1112, date=today, subject='lecture3')
    add_lecture(lecture_id=994, course_id=1114, date=today, subject='lecture4')
