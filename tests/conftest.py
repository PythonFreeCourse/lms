import datetime

from lmsweb.models import ALL_MODELS, Role, RoleOptions, User, Exercise, Comment

from peewee import SqliteDatabase

import pytest

SUBJECT = 'python'
COMMENT_TEXT = "very good!"


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
def user(populate_roles):
    admin_role = Role.get(Role.name == RoleOptions.STAFF.value)
    return User.create(  # NOQA: S106
            username='Ido',
            fullname='Elk',
            mail_address='mymail@mail.com',
            password='fake pass',
            saltedhash='asd',
            role=admin_role,
    )


@pytest.fixture()
def admin_user(populate_roles):
    admin_role = Role.get(Role.name == RoleOptions.ADMINISTRATOR.value)
    return User.create(  # NOQA: S106
            username='Yam',
            fullname='Elk',
            mail_address='mymail@mail.com',
            password='fake pass',
            role=admin_role,
    )


@pytest.fixture()
def exercise(user):
    return Exercise.create(
            subject=SUBJECT,
            date=datetime.datetime.now(),
            is_archived=False,
    )


@pytest.fixture()
def comment(user, exercise):
    return Comment.create(
            commenter=user,
            timestamp=datetime.datetime.now(),
            exercise=exercise,
            comment_text=COMMENT_TEXT,
            line_number=1,
    )
