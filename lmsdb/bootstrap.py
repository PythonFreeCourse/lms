from lmsdb.models import (
    User, database, ALL_MODELS, Role, create_basic_roles, create_demo_users
)

with database.connection_context():
    database.create_tables(ALL_MODELS, safe=True)

    if Role.select().count() == 0:
        create_basic_roles()
    if User.select().count() == 0:
        create_demo_users()
