from typing import Type

from peewee import Model, Field
from playhouse.migrate import migrate

from lms.lmsdb import database_config, database  # noqa: I100
from lms.lmsdb import models
from lmsdb.models import User
from lms.lmstests.public.flake8 import text_fixer

_DUMMY_EXERCISE_DATA = {
    models.Exercise.subject.name: 'subj',
    models.Exercise.date.name: datetime.now(),
    models.Exercise.is_archived.name: False,
    models.Exercise.notebook_num.name: 1,
}
_DUMMY_COMMENT_TEXT = {
    models.CommentText.text.name: 'test',
    models.CommentText.flake8_key.name: 'DUMMY',
}

_DUMMY_SOLUTION = {
    models.Solution.exercise.name: models.Exercise.create(**_DUMMY_EXERCISE_DATA),
    models.Solution.solver.name: User.get_by_id(1),
    models.Solution.json_data_str.name: 'test',
    models.Solution.submission_timestamp.name: datetime.now(),
}


def _migrate_column_in_table_if_needed(
    table: Type[Model],
    field_instance: Field,
):
    column_name = field_instance.name
    table_name = table.__name__.lower()
    cols = {col.name for col in database.get_columns(table_name)}

    if column_name in cols:
        print(f'No need to create {column_name} column for table {table}')  # noqa: T001
        return

    print(f'create {column_name} field in {table}')  # noqa: T001
    migrator = database_config.get_migrator_instance()
    with database_config.database.transaction():
        migrate(migrator.add_column(
            table_name,
            field_instance.name,
            field_instance,
        ))
        database_config.database.commit()


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


def _add_is_auto_needed():
    return _migrate_column_in_table_if_needed(
        models.Comment,
        models.Comment.is_auto,
    )


def main():
    with models.database.connection_context():
        models.database.create_tables(models.ALL_MODELS, safe=True)

        if models.Role.select().count() == 0:
            models.create_basic_roles()
        if models.User.select().count() == 0:
            models.create_demo_users()

    _add_flake8_key_if_needed()
    text_fixer.fix_texts()
    _add_notebook_num_if_needed()
    _add_is_auto_needed()
    _add_order_if_needed()


if __name__ == '__main__':
    main()
