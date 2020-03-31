from lms.lmsdb import models


def main():
    with models.database.connection_context():
        models.database.create_tables(models.ALL_MODELS, safe=True)

        if models.Role.select().count() == 0:
            models.create_basic_roles()
        if models.User.select().count() == 0:
            models.create_demo_users()


if __name__ == '__main__':
    main()
