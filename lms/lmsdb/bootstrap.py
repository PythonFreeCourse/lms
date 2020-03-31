from peewee import ProgrammingError

from playhouse.migrate import migrate

from lms.lmsdb import database_config  # noqa: I100
from lms.lmsdb import models


def _add_flake8_key_if_needed():
    exists = True
    try:
        with database_config.database.atomic():
            models.CommentText.create_comment('dummy222', 'dummy222')
            database_config.database.rollback()
    except ProgrammingError:
        exists = False
        database_config.database.close()

    if exists:
        print('No need to create flake8_key')  # noqa: T001
        return

    print('create flake_key field')  # noqa: T001
    migrator = database_config.get_migrator_instance()
    with database_config.database.transaction():
        migrate(migrator.add_column(
            'commenttext',
            models.CommentText.flake8_key.name,
            models.CommentText.flake8_key,
        ))
        database_config.database.commit()


def main():
    with models.database.connection_context():
        models.database.create_tables(models.ALL_MODELS, safe=True)

        if models.Role.select().count() == 0:
            models.create_basic_roles()
        if models.User.select().count() == 0:
            models.create_demo_users()

    _add_flake8_key_if_needed()


if __name__ == '__main__':
    main()
