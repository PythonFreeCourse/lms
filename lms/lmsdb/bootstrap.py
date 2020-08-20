import sys
import logging
from typing import Any, Optional, Type

from peewee import (  # type: ignore
    Entity, Expression, Field, ForeignKeyField, Model, OP,
    OperationalError, ProgrammingError, SQL, TextField,
)
from playhouse.migrate import migrate  # type: ignore

from lms.lmsdb import database_config as db_config
from lms.lmsdb import models
from lms.lmstests.public.flake8 import text_fixer
from lms.lmstests.public.unittests import import_tests


logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


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


def _add_index_if_needed(
    table: Type[Model],
    field_instance: Field,
    is_unique_constraint: bool = False,
) -> None:
    column_name = field_instance.name
    table_name = table.__name__.lower()
    migrator = db_config.get_migrator_instance()
    log.info(f"Add index to '{column_name}' field in '{table_name}'")
    with db_config.database.transaction():
        try:
            migrate(
                migrator.add_index(
                    table_name, (column_name,), is_unique_constraint,
                ),
            )
        except (OperationalError, ProgrammingError) as e:
            if 'already exists' in str(e):
                log.info('Index already exists.')
            else:
                raise
        db_config.database.commit()


def _drop_index_if_needed(
    table: Type[Model],
    field_instance: Field,
    foreign_key: bool = False,
) -> None:
    table_name = table.__name__.lower()
    suffix = '_id' if foreign_key else ''
    column_name = f'{table_name}_{field_instance.name}{suffix}'
    migrator = db_config.get_migrator_instance()
    log.info(f"Drop index from '{column_name}' field in '{table_name}'")
    with db_config.database.transaction():
        try:
            migrate(migrator.drop_index(table_name, column_name))
        except (OperationalError, ProgrammingError) as e:
            if 'does not exist' in str(e):
                log.info('Index already exists.')
            else:
                raise
        db_config.database.commit()


def _add_indices_if_needed():
    table_field_pairs = (
        (models.Notification, models.Notification.created),
        (models.Notification, models.Notification.related_id),
        (models.Exercise, models.Exercise.is_archived),
        (models.Exercise, models.Exercise.order),
        (models.Solution, models.Solution.state),
        (models.Solution, models.Solution.submission_timestamp),
    )
    for table, field_instance in table_field_pairs:
        _add_index_if_needed(table, field_instance)


def _add_solution_state_if_needed():
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


def _update_solution_hashes(s):
    log.info('Updating solution hashes. Might take a while.')
    create_hash = models.Solution.create_hash
    for solution in s:
        solution.hashed = create_hash(solution.json_data_str)
        solution.save()


def check_if_multiple_files_migration_is_needed():
    db = db_config.database
    solution_cols = {
        col.name for col in db.get_columns(models.Solution.__name__.lower())
    }
    if 'json_data_str' not in solution_cols:
        log.info('Skipping multiple files migration.')
        return False
    return True


def _multiple_files_migration() -> bool:
    f = models.SolutionFile

    # Mock old solution. The null is needed for peewee's ALTER.
    class Solution(models.Solution):
        json_data_str = TextField(column_name='json_data_str')
        hashed = TextField(null=True)
    s = Solution

    # Mock old comment. The null is needed for peewee's ALTER.
    class Comment(models.Comment):
        file = ForeignKeyField(f, backref='comments', null=True)
    c = Comment

    # Check if the migration is needed.
    if not check_if_multiple_files_migration_is_needed():
        return False

    # Create Solution.hashed and populate it using json_data_str
    _migrate_column_in_table_if_needed(s, s.hashed)
    _update_solution_hashes(s)

    # Copy the data from Solution to SolutionFile with the same id.
    # This will allow us to redirect Comment.solution_id from pointing to
    # Solution to pointing to SolutionFile, keeping old comments.
    solutions = s.select(
        s.id, s.id, '/main.py', s.json_data_str, s.hashed,
    )
    fields = [f.id, f.solution, f.path, f.code, f.file_hash]
    f.insert_from(solutions, fields).execute()
    _migrate_copy_column(c, dest='file_id', source='solution_id')
    _drop_column_from_module_if_needed(c, 'solution_id')

    # Add NOT NULL (can't use NOT NULL when ALTERing new columns)
    _add_not_null(c, 'file_id')
    _add_not_null(s, 'hashed')

    # Drop the unneeded content code of solutions
    _drop_column_from_module_if_needed(s, 'json_data_str')

    # Update serial of SolutionFile to the last one.
    # This will allow us to add new files without collusions.
    _execute_sql_if_possible(
        'SELECT setval('
        "pg_get_serial_sequence('{table_name}', 'id'), "
        'coalesce(max(id)+1, 1), '
        'false'
        ') FROM {table_name};'.format(table_name='solutionfile'),
    )

    # Done
    log.info('Successfully migrated multiple files.')
    return True


def _prepare_postgres_to_multiple_files_migration() -> bool:
    # Check if the migration is needed.
    if not check_if_multiple_files_migration_is_needed():
        return False

    class Comment(models.Comment):
        file = ForeignKeyField(
            models.SolutionFile, backref='comments', null=True,
        )
    c = Comment

    # Trick peewee to think there is a file column with no index,
    # # than create it in the real Comments table
    _drop_index_if_needed(c, c.file, foreign_key=True)

    # Create Comments.file_id
    _migrate_column_in_table_if_needed(c, c.file, field_name='file_id')
    return True


def main():
    with models.database.connection_context():
        models.database.create_tables([models.SolutionFile], safe=True)

    _prepare_postgres_to_multiple_files_migration()

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
    _add_solution_state_if_needed()
    _add_indices_if_needed()
    _multiple_files_migration()
    text_fixer.fix_texts()
    import_tests.load_tests_from_path('/app_dir/notebooks-tests')


if __name__ == '__main__':
    main()
