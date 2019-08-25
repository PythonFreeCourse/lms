import datetime

from lmsweb.models import ALL_MODELS, Course, Lecture, Role, RoleOptions, User

from peewee import SqliteDatabase

import pytest


@pytest.fixture(autouse=True, scope='session')
def db_in_memory():
    """Binds all models to in-memory SQLite and creates all tables`"""
    db = SqliteDatabase(':memory:')
    db.bind(ALL_MODELS)
    db.connect()
    db.create_tables(ALL_MODELS)

    yield db

    db.drop_tables(ALL_MODELS)
    db.close()


@pytest.fixture(autouse=True, scope='function')
def db(db_in_memory):
    """Rollback all operations between each test-case"""
    with db_in_memory.atomic():
        yield db_in_memory
        db_in_memory.rollback()


@pytest.fixture()
def populate_roles():
    for role in RoleOptions:
        Role.create(name=role.value)


@pytest.fixture()
def course():
    course_name = 'Python 1'
    open_date = datetime.datetime.now()
    return Course.create(name=course_name, open_date=open_date)


@pytest.fixture()
def user(populate_roles):
    admin_role = Role.get(Role.name == RoleOptions.STAFF_ROLE.value)
    return User.create(  # NOQA: S106
        username='Ido',
        fullname='Elk',
        mail_address='mymail@mail.com',
        password='fake pass',
        role=admin_role,
    )


@pytest.fixture()
def admin_user(populate_roles):
    admin_role = Role.get(Role.name == RoleOptions.ADMINISTRATOR_ROLE.value)
    return User.create(  # NOQA: S106
        username='Yam',
        fullname='Elk',
        mail_address='mymail@mail.com',
        password='fake pass',
        role=admin_role,
    )


@pytest.fixture()
def lecture(course):
    lecture_date = datetime.datetime.now()
    subject = 'Intro'
    return Lecture.create(
        subject=subject,
        course=course,
        date=lecture_date,
    )
