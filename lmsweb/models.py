from flask_admin import Admin
from flask_admin.contrib.peewee import ModelView

from lmsweb import app

from peewee import (
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    IntegrityError,
    Model,
    PostgresqlDatabase,
)

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


class User(BaseModel):
    username = CharField(unique=True)
    fullname = CharField()
    mail_address = CharField()
    password = CharField()
    user_type = CharField()

    def is_student(self):
        return User.user_type == 'is_student'

    def is_teacher(self):
        return User.user_type == 'teacher'

    def get_user_courses(self):
        return (
            Course.select()
            .join(UserCourseRelationship, on=UserCourseRelationship.course)
            .where(UserCourseRelationship.user == self)
            .order_by(Course.id)
        )


class Course(BaseModel):
    course_id = IntegerField(unique=True)
    name = CharField()
    open_date = DateTimeField()

    def get_course_administrators(self):
        is_this_course = UserCourseRelationship.course == self
        return (
            User.select()
            .join(UserCourseRelationship, on=UserCourseRelationship.user)
            .where(is_this_course & UserCourseRelationship.is_admin)
        )


class UserCourseRelationship(BaseModel):
    user = ForeignKeyField(User, backref='user')
    course = ForeignKeyField(Course, backref='course')
    is_admin = BooleanField(default=False)


class Lecture(BaseModel):
    lecture_id = IntegerField(unique=True)
    course = ForeignKeyField(Course, backref='lectures')
    date = DateTimeField()
    subject = CharField()

    def get_participants(self):
        return (
            User.select()
            .join(UserLectureRelationship, on=UserLectureRelationship.user)
            .where(UserLectureRelationship.lecture == self)
        )


class UserLectureRelationship(BaseModel):
    user = ForeignKeyField(User, backref='user')
    lecture = ForeignKeyField(Lecture, backref='lecture')


# Examples
def get_object(model, *expressions):
    return model.get(*expressions)


def add_course(course_id, name, open_date):
    course = Course(course_id=course_id, name=name, open_date=open_date)
    if course.save() != 1:
        raise IntegrityError()
    return course


def add_user(username, fullname, mail_address, password, user_type):
    user = User(**locals())
    if user.save(force_insert=True) != 1:
        raise IntegrityError()
    return user


def add_lecture(lecture_id, course_id, date, subject):
    course = get_object(Course, Course.course_id == course_id)
    lecture = Lecture(
        lecture_id=lecture_id, course=course, date=date, subject=subject,
    )
    if lecture.save(force_insert=True) != 1:
        raise IntegrityError()
    return lecture


# 1. Add a user to course
def user_add_to_course(username, course_id, is_admin=False):
    try:
        user = get_object(User, User.username == username)
        course = get_object(Course, Course.course_id == course_id)
        with database.atomic():
            UserCourseRelationship.create(
                user=user, course=course, is_admin=is_admin,
            )
    except IntegrityError:
        return False
    return True


# 2. Remove user from course
def user_remove_from_course(username, course_id):
    user = get_object(User, User.username == username)
    course = get_object(Course, Course.course_id == course_id)
    is_user_match = UserCourseRelationship.user == user
    is_course_match = UserCourseRelationship.course == course
    is_user_and_course_match = is_user_match & is_course_match
    UserCourseRelationship.delete().where(is_user_and_course_match).execute()


# 3. Get all lectures of a specific course
def course_get_lectures(course_id):
    return Lecture.select().join(Course).where(Course.course_id == course_id)


# 4. Sign a user a participant in a lecture
def user_add_to_lecture(username, lecture_id):
    try:
        # NOQA: TODO: Make sure user is enlisted in the lecture's course
        user = get_object(User, User.username == username)
        lecture = get_object(Lecture, Lecture.lecture_id == lecture_id)
        with database.atomic():
            UserLectureRelationship.create(user=user, lecture=lecture)
    except IntegrityError:
        return False
    return True


# 5. Get lecture participants
def lecture_get_participants(lecture_id):
    lecture = get_object(Lecture, Lecture.lecture_id == lecture_id)
    return lecture.get_participants()


# 6. Get user's courses
def user_get_courses(username):
    user = get_object(User, User.username == username)
    return user.get_user_courses()


# 7. Get course's administrators
def course_get_administrators(course_id):
    course = get_object(Course, Course.course_id == course_id)
    return course.get_course_administrators()


ALL_MODELS = (User, Course, Lecture)

# set optional bootswatch theme
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'

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
