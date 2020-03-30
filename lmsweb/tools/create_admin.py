from flask_admin import AdminIndexView
from flask_admin.contrib.peewee import ModelView  # type: ignore
from flask_login import current_user  # type: ignore

from lmsweb import webapp
from lmsdb import database
from lmsdb.models import (
    Admin,
    ALL_MODELS,
    Role,
    create_basic_roles,
    create_demo_users, User)
