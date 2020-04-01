from peewee import ProgrammingError

from playhouse.migrate import migrate

from lms.lmsdb import database_config  # noqa: I100
from lms.lmsdb import models
from lms.lmstests.sandbox.flake8 import defines


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


def _update_flake8_texts():
    print('Update flake8 texts')  # noqa: T001
    with database_config.database.atomic():
        for flake8_key, text in defines.FLAKE_ERRORS_MAPPING.items():
            models.CommentText.update(**{
             models.CommentText.text.name: text,
            }).where(models.CommentText.flake8_key == flake8_key).execute()


def _delete_whitelist_comments():
    print('Delete comments that listed in whitelist')  # noqa: T001
    with database_config.database.atomic():
        for flake8_key in defines.FLAKE_SKIP_ERRORS:
            for comment in models.Comment.select().join(
                    models.CommentText,
            ).where(models.CommentText.flake8_key == flake8_key):
                comment.delete().execute()

            models.CommentText.delete().where(
                models.CommentText.flake8_key == flake8_key,
            ).execute()


def main():
    with models.database.connection_context():
        models.database.create_tables(models.ALL_MODELS, safe=True)

        if models.Role.select().count() == 0:
            models.create_basic_roles()
        if models.User.select().count() == 0:
            models.create_demo_users()

        _update_flake8_texts()
        _delete_whitelist_comments()

    _add_flake8_key_if_needed()


if __name__ == '__main__':
    main()
