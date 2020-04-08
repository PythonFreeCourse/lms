from typing import Type

from peewee import Field, Model, fn  # type: ignore
from playhouse.migrate import migrate  # type: ignore

from lms.lmsdb import database_config as db_config
from lms.lmsdb import models
from lms.lmstests.public.flake8 import text_fixer


def _migrate_column_in_table_if_needed(
    table: Type[Model],
    field_instance: Field,
) -> bool:
    column_name = field_instance.name
    table_name = table.__name__.lower()
    cols = {col.name for col in db_config.database.get_columns(table_name)}

    if column_name in cols:
        print(f'Column {column_name} already exists in {table}')  # noqa: T001
        return False

    print(f'Create {column_name} field in {table}')  # noqa: T001
    migrator = db_config.get_migrator_instance()
    with db_config.database.transaction():
        migrate(migrator.add_column(
            table_name,
            field_instance.name,
            field_instance,
        ))
        db_config.database.commit()
    return True


def _add_flake8_key_if_needed():
    return _migrate_column_in_table_if_needed(
        models.CommentText,
        models.CommentText.flake8_key,
    )


def _add_notebook_num_if_needed():
    return _migrate_column_in_table_if_needed(
        models.Exercise,
        models.Exercise.notebook_num,
    )


def _add_order_if_needed():
    return _migrate_column_in_table_if_needed(
        models.Exercise,
        models.Exercise.order,
    )


def _add_is_auto_if_needed():
    return _migrate_column_in_table_if_needed(
        models.Comment,
        models.Comment.is_auto,
    )


def _add_latest_solution_if_needed():
    return _migrate_column_in_table_if_needed(
        models.Solution,
        models.Solution.latest_solution,
    )


def main():
    with models.database.connection_context():
        models.database.create_tables(models.ALL_MODELS, safe=True)

        if models.Role.select().count() == 0:
            models.create_basic_roles()
        if models.User.select().count() == 0:
            models.create_demo_users()

    _add_flake8_key_if_needed()
    _add_notebook_num_if_needed()
    _add_is_auto_if_needed()
    _add_latest_solution_if_needed()
    _add_order_if_needed()
    text_fixer.fix_texts()


if __name__ == '__main__':
    main()
