from typing import Type

from peewee import Field, Model, TextField  # type: ignore
from playhouse.migrate import migrate  # type: ignore

from lms.lmsdb import database_config as db_config
from lms.lmsdb import models
from lms.lmstests.public.flake8 import text_fixer
from lms.lmstests.public.unittests import import_tests


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


def _rename_column_in_table_if_needed(
    table: Type[Model],
    old_column_name: str,
    new_column_name: str,
) -> bool:
    column_name = old_column_name.lower()
    table_name = table.__name__.lower()
    cols = {col.name for col in db_config.database.get_columns(table_name)}

    if new_column_name in cols:
        print(f'Column {new_column_name} already exists in {table}')  # noqa: T001, E501
        return False
    if old_column_name not in cols:
        print(f'Column {old_column_name} not exists in {table}')  # noqa: T001, E501
        return False

    print(f'Changing {column_name} -> {new_column_name} in {table}')  # noqa: T001, E501
    migrator = db_config.get_migrator_instance()
    with db_config.database.transaction():
        migrate(
            migrator.rename_column(
                table_name, old_column_name, new_column_name,
            ),
        )
        db_config.database.commit()
    return True


def _alter_column_type_if_needed(
    table: Type[Model],
    field_instance: Field,
    new_type: Field,
) -> bool:
    field_type_name = new_type.__class__.__name__
    current_type = field_instance.__class__.__name__
    column_name = field_instance.name.lower()
    table_name = table.__name__.lower()

    if field_type_name.lower() == current_type.lower():
        print(f'Column {column_name} is already {field_type_name}')  # noqa: T001, E501
        return False

    print(  # noqa: T001
        f'Changing {column_name} from {current_type} '
        f'to {field_type_name} in {table}',
    )
    migrator = db_config.get_migrator_instance()
    with db_config.database.transaction():
        migrate(
            migrator.alter_column_type(table_name, column_name, new_type),
        )
        db_config.database.commit()
    return True


def _drop_column_from_module_if_needed(
    table: Type[Model],
    column_name: str,
) -> bool:
    table_name = table.__name__.lower()
    cols = {col.name for col in db_config.database.get_columns(table_name)}

    if column_name not in cols:
        print(f'Column {column_name} not exists in {table}')  # noqa: T001
        return False

    print(f'Drop {column_name} field in {table}')  # noqa: T001
    migrator = db_config.get_migrator_instance()
    with db_config.database.transaction():
        migrate(migrator.drop_column(
            table_name,
            column_name,
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


def _add_exercise_due_date_if_needed():
    return _migrate_column_in_table_if_needed(
        models.Exercise,
        models.Exercise.due_date,
    )


def _add_is_auto_if_needed():
    return _migrate_column_in_table_if_needed(
        models.Comment,
        models.Comment.is_auto,
    )


def _upgrade_notifications_if_needed():
    t = models.Notification
    _migrate_column_in_table_if_needed(t, t.action_url)
    _rename_column_in_table_if_needed(t, 'message_parameters', 'message')
    _rename_column_in_table_if_needed(t, 'related_object_id', 'related_id')
    _rename_column_in_table_if_needed(t, 'marked_read', 'viewed')
    _rename_column_in_table_if_needed(t, 'read', 'viewed')
    _rename_column_in_table_if_needed(t, 'notification_type', 'kind')
    _alter_column_type_if_needed(t, t.message, TextField())


def add_solution_state_if_needed():
    _migrate_column_in_table_if_needed(models.Solution, models.Solution.state)
    table_name = models.Solution.__name__.lower()
    cols = {col.name for col in db_config.database.get_columns(table_name)}
    latest_solution_migrate_ran = 'latest_solution' in cols
    is_checked_migrate_ran = 'is_checked' in cols

    if latest_solution_migrate_ran:
        models.database.execute_sql(
            'update solution set state=%s '
            'where latest_solution = %s',
            params=(
                models.Solution.STATES.OLD_SOLUTION.name,
                False,
            ),
        )
        _drop_column_from_module_if_needed(
            models.Solution,
            'latest_solution',
        )

    if is_checked_migrate_ran:
        models.database.execute_sql(
            'update solution set state=%s '
            'where is_checked = %s',
            params=(
                models.Solution.STATES.DONE.name,
                True,
            ),
        )

        _drop_column_from_module_if_needed(
            models.Solution,
            'is_checked',
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
    _add_order_if_needed()
    _add_exercise_due_date_if_needed()
    _upgrade_notifications_if_needed()
    add_solution_state_if_needed()
    text_fixer.fix_texts()
    import_tests.load_tests_from_path('/app_dir/notebooks-tests')


if __name__ == '__main__':
    main()
