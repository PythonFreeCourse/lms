import datetime

from lms.lmsdb.models import (
    ALL_MODELS, Comment, CommentText,
    Exercise, Role, RoleOptions, Solution, User,
)

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


@pytest.fixture(autouse=True, scope='session')
def populate_roles():
    for role in RoleOptions:
        Role.create(name=role.value)


@pytest.fixture(autouse=True, scope='function')
def db(db_in_memory):
    """Rollback all operations between each test-case"""
    with db_in_memory.atomic():
        yield db_in_memory
        db_in_memory.rollback()


@pytest.fixture()
def staff_password():
    return 'fake pass'


@pytest.fixture()
def staff_user(staff_password):
    staff_role = Role.get(Role.name == RoleOptions.STAFF.value)
    return User.create(  # NOQA: S106
        username='Ido',
        fullname='Elk',
        mail_address='mymail@mail.com',
        password=staff_password,
        role=staff_role,
    )


@pytest.fixture()
def student_user():
    return create_student_user()


def create_student_user(index=0):
    return User.create(  # NOQA: S106
        username=f'student-{index}',
        fullname='Astudent',
        mail_address=f'so-student-{index}@mail.com',
        password='fake pass',
        role=Role.get_student_role(),
    )


@pytest.fixture()
def admin_user():
    admin_role = Role.get(Role.name == RoleOptions.ADMINISTRATOR.value)
    return User.create(  # NOQA: S106
        username='Yam',
        fullname='Elk',
        mail_address='mymail@mail.com',
        password='fake pass',
        role=admin_role,
    )


@pytest.fixture()
def exercise():
    return Exercise.create(
        subject='python',
        date=datetime.datetime.now(),
        is_archived=False,
    )


@pytest.fixture()
def solution(exercise, student_user):
    return Solution.create_solution(
        exercise=exercise,
        solver=student_user,
    )


@pytest.fixture()
def comment(staff_user, solution):
    return Comment.create_comment(
        commenter=staff_user,
        solution=solution,
        comment_text=CommentText.create_comment(text='very good!'),
        line_number=1,
        is_auto=False,
    )[0]
