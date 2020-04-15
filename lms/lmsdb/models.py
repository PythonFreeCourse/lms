import enum
import random
import secrets
import string
from datetime import datetime
from typing import Any, ClassVar, Dict, Iterable, Optional, Tuple

from flask_login import UserMixin  # type: ignore
from peewee import (  # type: ignore
    BooleanField, Case, CharField, Check, DateTimeField, ForeignKeyField,
    IntegerField, ManyToManyField, TextField, fn,
)
from playhouse.signals import Model, post_save, pre_save  # type: ignore
from werkzeug.security import (
    check_password_hash, generate_password_hash,
)

from lms.lmsdb import database_config


database = database_config.get_db_instance()
ExercisesDictById = Dict[int, Dict[str, Any]]


class RoleOptions(enum.Enum):
    STUDENT = 'Student'
    STAFF = 'Staff'
    ADMINISTRATOR = 'Administrator'

    def __str__(self):
        return self.value


class BaseModel(Model):
    class Meta:
        database = database

    def refresh(self) -> 'BaseModel':
        return type(self).get(self._pk_expr())


class Role(BaseModel):
    name = CharField(unique=True, choices=(
        (RoleOptions.ADMINISTRATOR.value,
         RoleOptions.ADMINISTRATOR.value),
        (RoleOptions.STAFF.value, RoleOptions.STAFF.value),
        (RoleOptions.STUDENT.value, RoleOptions.STUDENT.value),
    ))

    def __str__(self):
        return self.name

    @classmethod
    def get_student_role(cls):
        return cls.get(Role.name == RoleOptions.STUDENT.value)

    @classmethod
    def get_staff_role(cls):
        return cls.get(Role.name == RoleOptions.STAFF.value)

    @classmethod
    def by_name(cls, name):
        if name.startswith('_'):
            raise ValueError('That could lead to a security issue.')
        role_name = getattr(RoleOptions, name.upper()).value
        return cls.get(name=role_name)

    @property
    def is_student(self):
        return self.name == RoleOptions.STUDENT.value

    @property
    def is_staff(self):
        return self.name == RoleOptions.STAFF.value

    @property
    def is_administrator(self):
        return self.name == RoleOptions.ADMINISTRATOR.value

    @property
    def is_manager(self):
        return self.is_staff or self.is_administrator


class User(UserMixin, BaseModel):
    username = CharField(unique=True)
    fullname = CharField()
    mail_address = CharField(unique=True)
    password = CharField()
    role = ForeignKeyField(Role, backref='users')

    def is_password_valid(self, password):
        return check_password_hash(self.password, password)

    @classmethod
    def get_system_user(cls) -> 'User':
        instance, _ = cls.get_or_create(**{
            cls.mail_address.name: 'linter-checks@python.guru',
            User.username.name: 'linter-checks@python.guru',
        }, defaults={
            User.fullname.name: 'Checker guru',
            User.role.name: Role.get_staff_role(),
            User.password.name: cls.random_password(),
        })
        return instance

    @classmethod
    def random_password(cls) -> str:
        return ''.join(random.choices(string.printable.strip()[:65], k=12))

    def __str__(self):
        return f'{self.username} - {self.fullname}'


@pre_save(sender=User)
def on_save_handler(model_class, instance, created):
    """Hashes password on creation/save"""

    # If password changed then it won't start with hash's method prefix
    is_password_changed = not instance.password.startswith('pbkdf2:sha256')
    if created or is_password_changed:
        instance.password = generate_password_hash(instance.password)


class Notification(BaseModel):
    ID_FIELD_NAME = 'id'
    MAX_PER_USER = 10

    user = ForeignKeyField(User)
    created = DateTimeField(default=datetime.now)
    notification_type = CharField()
    message_parameters = database_config.JsonField()
    related_object_id = IntegerField()
    marked_read = BooleanField(default=False)

    def mark_as_read(self):
        self.marked_read = True
        self.save()

    @classmethod
    def notifications_for_user(
            cls,
            for_user: User,
    ) -> Iterable['Notification']:
        return cls.select().join(User).filter(
            cls.user == for_user.id).limit(cls.MAX_PER_USER)

    @classmethod
    def create_notification(
            cls,
            user: User,
            notification_type: str,
            message_parameters: dict,
            related_object_id: int,
    ) -> 'Notification':
        return cls.create(**{
            cls.user.name: user,
            cls.notification_type.name: notification_type,
            cls.message_parameters.name: message_parameters,
            cls.related_object_id.name: related_object_id,
        })


@post_save(sender=Notification)
def on_notification_saved(
        model_class: ClassVar,
        instance: Notification,
        created: datetime,
):
    # sqlite supports delete query with order
    # but when we use postgres, peewee is stupid
    old_notifications = Notification.select().where(
        Notification.user == instance.user.id,
    ).order_by(
        Notification.created.desc(),
    ).offset(Notification.MAX_PER_USER)
    for instance in old_notifications:
        instance.delete_instance()


class Exercise(BaseModel):
    subject = CharField()
    date = DateTimeField()
    users = ManyToManyField(User, backref='exercises')
    is_archived = BooleanField()
    due_date = DateTimeField(null=True)
    notebook_num = IntegerField(default=0)
    order = IntegerField(default=0)

    def open_for_new_solutions(self) -> bool:
        if self.due_date is None:
            return not self.is_archived
        return datetime.now() < self.due_date and not self.is_archived

    @classmethod
    def get_objects(cls, fetch_archived: bool = False):
        exercises = cls.select().order_by(Exercise.id)
        if not fetch_archived:
            exercises = exercises.where(cls.is_archived == False)  # NOQA: E712
        return exercises

    def as_dict(self) -> Dict[str, Any]:
        return {
            'exercise_id': self.id,
            'exercise_name': self.subject,
            'is_archived': self.is_archived,
            'notebook': self.notebook_num,
            'due_date': self.due_date,
        }

    @staticmethod
    def as_dicts(exercises: Iterable['Exercise']) -> ExercisesDictById:
        return {exercise.id: exercise.as_dict() for exercise in exercises}

    def __str__(self):
        return self.subject


class SolutionState(enum.Enum):
    CREATED = 'Created'
    IN_CHECKING = 'In checking'
    DONE = 'Done'
    OLD_SOLUTION = 'Old solution'

    @classmethod
    def active_solutions(cls) -> Iterable[str]:
        return (
            cls.DONE.name,
            cls.IN_CHECKING.name,
            cls.CREATED.name,
        )

    @classmethod
    def to_choices(cls) -> Tuple[Tuple[str, str]]:
        return tuple((choice.name, choice.value) for choice in tuple(cls))


class Solution(BaseModel):
    STATES = SolutionState
    MAX_CHECK_TIME_SECONDS = 60 * 10

    exercise = ForeignKeyField(Exercise, backref='solutions')
    solver = ForeignKeyField(User, backref='solutions')
    checker = ForeignKeyField(User, null=True, backref='solutions')
    state = CharField(
        choices=STATES.to_choices(),
        default=STATES.CREATED.name,
    )
    grade = IntegerField(
        default=0, constraints=[Check('grade <= 100'), Check('grade >= 0')],
    )
    submission_timestamp = DateTimeField()
    json_data_str = TextField()

    @property
    def is_checked(self):
        return self.state == self.STATES.DONE.name

    def start_checking(self) -> bool:
        return self.set_state(Solution.STATES.IN_CHECKING)

    def set_state(self, new_state: SolutionState, **kwargs) -> bool:
        # Optional: filter the old state of the object
        # to make sure that no two processes set the state together
        requested_solution = (Solution.id == self.id)
        changes = Solution.update(
            **{Solution.state.name: new_state.name},
            **kwargs,
        ).where(requested_solution)
        updated = changes.execute() == 1
        return updated

    @property
    def code(self):
        return self.json_data_str

    def ordered_versions(self) -> Iterable['Solution']:
        return Solution.select().filter(
            Solution.exercise == self.exercise,
            Solution.solver == self.solver,
        ).order_by(Solution.submission_timestamp.asc())

    @classmethod
    def of_user(
            cls, user_id: int, with_archived: bool = False,
    ) -> Iterable[Dict[str, Any]]:
        db_exercises = Exercise.get_objects(fetch_archived=with_archived)
        exercises = Exercise.as_dicts(db_exercises)

        solutions = (
            cls
            .select(cls.exercise, cls.id, cls.state)
            .where(cls.exercise.in_(db_exercises), cls.solver == user_id)
            .order_by(cls.submission_timestamp.desc())
        )
        for solution in solutions:
            exercise = exercises[solution.exercise_id]
            if exercise.get('solution_id') is None:
                exercise['solution_id'] = solution.id
                exercise['is_checked'] = solution.is_checked
        return tuple(exercises.values())

    @property
    def comments(self):
        return Comment.select().join(Solution).filter(Comment.solution == self)

    @classmethod
    def solution_exists(
            cls,
            exercise: Exercise,
            solver: User,
            json_data_str: str,
    ):
        return cls.select().filter(
            cls.exercise == exercise,
            cls.solver == solver,
            cls.json_data_str == json_data_str,
        ).exists()

    @classmethod
    def create_solution(
        cls,
        exercise: Exercise,
        solver: User,
        json_data_str='',
    ):
        instance = cls.create(**{
            cls.exercise.name: exercise,
            cls.solver.name: solver,
            cls.submission_timestamp.name: datetime.now(),
            cls.json_data_str.name: json_data_str,
        })

        # update old solutions for this exercise
        other_solutions: Iterable[Solution] = cls.select().filter(
            cls.exercise == exercise,
            cls.solver == solver,
            cls.id != instance.id,
        )
        for old_solution in other_solutions:
            old_solution.set_state(Solution.STATES.OLD_SOLUTION)
        return instance

    @classmethod
    def next_unchecked(cls) -> Optional['Solution']:
        unchecked_exercises = cls.select().where(
            cls.state == Solution.STATES.CREATED.name,
        )
        try:
            return unchecked_exercises.get()
        except cls.DoesNotExist:
            return None

    @classmethod
    def next_unchecked_of(cls, exercise_id) -> Optional['Solution']:
        try:
            return cls.select().where(
                cls.state == cls.STATES.CREATED.name,
                cls.exercise == exercise_id,
            ).get()
        except cls.DoesNotExist:
            return None

    @classmethod
    def status(cls):
        one_if_is_checked = Case(
            Solution.state, ((Solution.STATES.DONE.name, 1),), 0)
        fields = [
            Exercise.id,
            Exercise.subject.alias('name'),
            Exercise.is_archived.alias('is_archived'),
            fn.Count(Solution.id).alias('submitted'),
            fn.Sum(one_if_is_checked).alias('checked'),
        ]

        join_by_exercise = (Solution.exercise == Exercise.id)
        active_solutions = Solution.state.in_(
            Solution.STATES.active_solutions())
        return (
            Exercise
            .select(*fields)
            .join(Solution, 'LEFT OUTER', on=join_by_exercise)
            .where(active_solutions)
            .group_by(Exercise.subject, Exercise.id)
            .order_by(Exercise.id)
        )


class CommentText(BaseModel):
    text = TextField(unique=True)
    flake8_key = TextField(null=True)

    @classmethod
    def create_comment(
            cls, text: str, flake_key: Optional[str] = None,
    ) -> 'CommentText':
        instance, _ = CommentText.get_or_create(
            **{CommentText.text.name: text},
            defaults={CommentText.flake8_key.name: flake_key},
        )
        return instance


class Comment(BaseModel):
    commenter = ForeignKeyField(User, backref='comments')
    timestamp = DateTimeField(default=datetime.now)
    line_number = IntegerField(constraints=[Check('line_number >= 1')])
    comment = ForeignKeyField(CommentText)
    solution = ForeignKeyField(Solution)
    is_auto = BooleanField(default=False)

    @classmethod
    def create_comment(
            cls,
            commenter: User,
            line_number: int,
            comment_text: CommentText,
            solution: Solution,
            is_auto: bool,
    ) -> 'Comment':
        return cls.get_or_create(
            commenter=commenter,
            line_number=line_number,
            comment=comment_text,
            solution=solution,
            is_auto=is_auto,
        )

    @classmethod
    def by_solution(cls, solution_id: int):
        fields = [
            Comment, CommentText.text, CommentText.flake8_key, CommentText.id,
        ]
        the_solution = Comment.solution == solution_id
        return Comment.select(*fields).join(CommentText).where(the_solution)

    @classmethod
    def get_solutions(cls, solution_id: int) -> Tuple[Dict[Any, Any], ...]:
        return tuple(cls.by_solution(solution_id).dicts())


def generate_password():
    randomizer = secrets.SystemRandom()
    length = randomizer.randrange(9, 16)
    password = randomizer.choices(string.printable[:66], k=length)
    return ''.join(password)


def create_demo_users():
    print('First run! Here are some users to get start with:')  # noqa: T001
    fields = ['username', 'fullname', 'mail_address', 'role']
    student_role = Role.by_name('Student')
    admin_role = Role.by_name('Administrator')
    entities = [
        ['lmsadmin', 'Admin', 'lms@pythonic.guru', admin_role],
        ['user', 'Student', 'student@pythonic.guru', student_role],
    ]

    for entity in entities:
        user = dict(zip(fields, entity))
        password = generate_password()
        User.create(**user, password=password)
        print(f"User: {user['username']}, Password: {password}")  # noqa: T001


def create_basic_roles():
    for role in RoleOptions:
        Role.create(name=role.value)


ALL_MODELS = BaseModel.__subclasses__()
