from typing import Any, Callable, Optional, Tuple, Type

from peewee import (
    Entity, Expression, Field, Model, OP, OperationalError, ProgrammingError,
    SQL,
)
from playhouse.migrate import migrate

from lms.lmsdb import database_config as db_config
from lms.lmsdb import models
from lms.lmstests.public.linters import text_fixer
from lms.lmstests.public.unittests import import_tests
from lms.utils.log import log


def _migrate_column_in_table_if_needed(
    table: Type[Model],
    field_instance: Field,
    *,
    field_name: Optional[str] = None,
    **kwargs: Any,
) -> bool:
    column_name = field_name or field_instance.name
    table_name = table.__name__.lower()
    cols = {col.name for col in db_config.database.get_columns(table_name)}

    if column_name in cols:
        log.info(f'Column {column_name} already exists in {table}')
        return False

    log.info(f'Create {column_name} field in {table}')
    migrator = db_config.get_migrator_instance()
    with db_config.database.transaction():
        try:
            migrate(migrator.add_column(
                table=table_name,
                column_name=column_name,
                field=field_instance,
                **kwargs,
            ))
        except (OperationalError, ProgrammingError) as e:
            if 'does not exist' in str(e):
                log.info(f'Column {field_name} already exists: {e}')
            else:
                raise
        db_config.database.commit()
    return True


def _migrate_copy_column(table: Type[Model], source: str, dest: str) -> bool:
    table_name = table.__name__.lower()
    migrator = db_config.get_migrator_instance()
    with db_config.database.transaction():
        (
            db_config.database.execute_sql(
                migrator.make_context()
                .literal('UPDATE ').sql(Entity(table_name))
                .literal(' SET ').sql(
                    Expression(
                        Entity(dest), OP.EQ, SQL(' solution_id'), flat=True,
                    ),
                ).query()[0],
            )
        )
    return True


def _drop_not_null(table: Type[Model], column_name: str) -> bool:
    table_name = table.__name__.lower()
    migrator = db_config.get_migrator_instance()
    with db_config.database.transaction():
        migrate(migrator.drop_not_null(table_name, column_name))
        db_config.database.commit()
    return True


def _add_not_null(table: Type[Model], column_name: str) -> bool:
    table_name = table.__name__.lower()
    migrator = db_config.get_migrator_instance()
    with db_config.database.transaction():
        migrate(migrator.add_not_null(table_name, column_name))
        db_config.database.commit()
    return True


def get_details(table: Model, column: Field) -> Tuple[bool, str, str]:
    table_name = table.__name__.lower()
    column_name = column.column_name

    cols = {col.name for col in db_config.database.get_columns(table_name)}
    if column_name in cols:
        return True, table_name, column_name
    return False, table_name, column_name


def _add_not_null_column(
    table: Model, column: Field,
    run_before_adding_not_null: Callable[[Model, Field], None] = None,
) -> bool:
    already_exists, table_name, column_name = get_details(table, column)
    log.info(f'Adding {table_name}.{column_name}, if needed.')
    if already_exists:
        log.info(f'Column {column_name} already exists in {table_name}.')
        return False

    migrator = db_config.get_migrator_instance()
    with db_config.database.transaction():
        column.null = True
        migrate(migrator.add_column(table_name, column_name, field=column))
        if callable(run_before_adding_not_null):
            run_before_adding_not_null(table, column)
        migrate(migrator.drop_not_null(table_name, column_name))
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
        log.info(f'Column {new_column_name} already exists in {table}')
        return False
    if old_column_name not in cols:
        log.info(f'Column {old_column_name} not exists in {table}')
        return False

    log.info(f'Changing {column_name} -> {new_column_name} in {table}')
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
        log.info(f'Column {column_name} is already {field_type_name}')
        return False

    log.info(
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
        log.info(f'Column {column_name} not exists in {table}')
        return False

    log.info(f'Drop {column_name} field in {table}')
    migrator = db_config.get_migrator_instance()
    with db_config.database.transaction():
        migrate(migrator.drop_column(table_name, column_name))
        db_config.database.commit()
    return True


def _execute_sql_if_possible(sql: str) -> bool:
    with db_config.database.transaction():
        log.info(f'Running {sql}')
        try:
            db_config.database.execute_sql(sql)
            db_config.database.commit()
        except (OperationalError, ProgrammingError) as e:
            log.info(f"Can't run SQL '{sql}' because: {e}")
    return True


def _drop_constraint_if_needed(table: Type[Model], column_name: str) -> bool:
    table_name = table.__name__.lower()
    cols = {col.name for col in db_config.database.get_columns(table_name)}

    if column_name not in cols:
        log.info(f'Column {column_name} not exists in {table}')
        return False

    log.info(f'Drop foreign key on {table}.{column_name}')
    migrator = db_config.get_migrator_instance()
    with db_config.database.transaction():
        migrate(migrator.drop_constraint(table_name, column_name))
        db_config.database.commit()
    return True


def has_column_named(table: Model, column_name: str) -> bool:
    db = db_config.database
    columns = {col.name for col in db.get_columns(table.__name__.lower())}
    if column_name not in columns:
        return False
    return True


def _add_api_keys_to_users_table(table: Model, _column: Field) -> None:
    log.info('Adding API Keys for all users, might take some extra time...')
    with db_config.database.transaction():
        for user in table:
            user.api_key = table.random_password(stronger=True)
            user.save()


def _api_keys_migration() -> bool:
    User = models.User
    _add_not_null_column(User, User.api_key, _add_api_keys_to_users_table)
    return True


def main():
    with models.database.connection_context():
        models.database.create_tables(models.ALL_MODELS, safe=True)

        if models.Role.select().count() == 0:
            models.create_basic_roles()
        if models.User.select().count() == 0:
            models.create_demo_users()

    _api_keys_migration()
    text_fixer.fix_texts()
    import_tests.load_tests_from_path('/app_dir/notebooks-tests')


if __name__ == '__main__':
    main()
