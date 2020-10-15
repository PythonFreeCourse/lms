from collections import Counter
import enum
import html
import secrets
import string
from datetime import datetime
from typing import (
    Any, Dict, Iterable, List, Optional, TYPE_CHECKING, Tuple,
    Type, Union, cast,
)

from flask_babel import gettext as _  # type: ignore
from flask_login import UserMixin  # type: ignore
from peewee import (  # type: ignore
    BooleanField, Case, CharField, Check, DateTimeField, ForeignKeyField,
    IntegerField, JOIN, ManyToManyField, TextField, fn,
)
from playhouse.signals import Model, post_save, pre_save  # type: ignore
from werkzeug.security import (
    check_password_hash, generate_password_hash,
)

from lms.lmsdb import database_config
from lms.models.errors import AlreadyExists
from lms.utils import hashing
from lms.utils.log import log


database = database_config.get_db_instance()
ExercisesDictById = Dict[int, Dict[str, Any]]
if TYPE_CHECKING:
    from lms.extractors.base import File


class RoleOptions(enum.Enum):
    BANNED = 'Banned'
    STUDENT = 'Student'
    STAFF = 'Staff'
    VIEWER = 'Viewer'
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
        (RoleOptions.ADMINISTRATOR.value, RoleOptions.ADMINISTRATOR.value),
        (RoleOptions.STAFF.value, RoleOptions.STAFF.value),
        (RoleOptions.VIEWER.value, RoleOptions.VIEWER.value),
        (RoleOptions.STUDENT.value, RoleOptions.STUDENT.value),
        (RoleOptions.BANNED.value, RoleOptions.BANNED.value),
    ))

    def __str__(self):
        return self.name

    @classmethod
    def get_banned_role(cls) -> 'Role':
        return cls.get(Role.name == RoleOptions.BANNED.value)

    @classmethod
    def get_student_role(cls) -> 'Role':
        return cls.get(Role.name == RoleOptions.STUDENT.value)

    @classmethod
    def get_staff_role(cls) -> 'Role':
        return cls.get(Role.name == RoleOptions.STAFF.value)

    @classmethod
    def get_admin_role(cls) -> 'Role':
        return cls.get(Role.name == RoleOptions.ADMINISTRATOR.value)

    @classmethod
    def by_name(cls, name) -> 'Role':
        if name.startswith('_'):
            raise ValueError('That could lead to a security issue.')
        role_name = getattr(RoleOptions, name.upper()).value
        return cls.get(name=role_name)

    @property
    def is_banned(self) -> bool:
        return self.name == RoleOptions.BANNED.value

    @property
    def is_student(self) -> bool:
        return self.name == RoleOptions.STUDENT.value

    @property
    def is_staff(self) -> bool:
        return self.name == RoleOptions.STAFF.value

    @property
    def is_administrator(self) -> bool:
        return self.name == RoleOptions.ADMINISTRATOR.value

    @property
    def is_manager(self) -> bool:
        return self.is_staff or self.is_administrator

    @property
    def is_viewer(self) -> bool:
        return self.name == RoleOptions.VIEWER.value or self.is_manager


class User(UserMixin, BaseModel):
    username = CharField(unique=True)
    fullname = CharField()
    mail_address = CharField(unique=True)
    password = CharField()
    role = ForeignKeyField(Role, backref='users')
    api_key = CharField()

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
            User.api_key.name: cls.random_password(),
        })
        return instance

    @classmethod
    def random_password(cls, stronger: bool = False) -> str:
        length_params = {'min_len': 40, 'max_len': 41} if stronger else {}
        return generate_string(**length_params)

    def get_notifications(self) -> Iterable['Notification']:
        return Notification.fetch(self)

    def __str__(self):
        return f'{self.username} - {self.fullname}'


@pre_save(sender=User)
def on_save_handler(model_class, instance, created):
    """Hash password on creation/save."""

    # If password changed then it won't start with hash's method prefix
    is_password_changed = not instance.password.startswith('pbkdf2:sha256')
    if created or is_password_changed:
        instance.password = generate_password_hash(instance.password)

    is_api_key_changed = not instance.api_key.startswith('pbkdf2:sha256')
    if created or is_api_key_changed:
        if not instance.api_key:
            instance.api_key = model_class.random_password()
        instance.api_key = generate_password_hash(instance.api_key)


class Notification(BaseModel):
    ID_FIELD_NAME = 'id'
    MAX_PER_USER = 10

    user = ForeignKeyField(User)
    created = DateTimeField(default=datetime.now, index=True)
    kind = IntegerField()
    message = TextField()
    related_id = IntegerField(null=True, index=True)
    action_url = CharField(null=True)
    viewed = BooleanField(default=False)

    def read(self) -> bool:
        self.viewed = True
        return bool(self.save())

    @classmethod
    def fetch(cls, user: User) -> Iterable['Notification']:
        user_id = cls.user == user.id
        return (
            cls
            .select()
            .join(User)
            .where(user_id)
            .order_by(Notification.created.desc())
            .limit(cls.MAX_PER_USER)
        )

    @classmethod
    def of(
            cls,
            related_id: int,
            user: Optional[int] = None,
    ) -> Iterable['Notification']:
        where_clause = [Notification.related_id == related_id]
        if user is not None:
            where_clause.append(Notification.user == user)

        return (
            cls
            .select()
            .join(User)
            .where(*where_clause)
            .limit(cls.MAX_PER_USER)
        )

    @classmethod
    def send(
        cls,
        user: User,
        kind: int,
        message: str,
        related_id: Optional[int] = None,
        action_url: Optional[str] = None,
    ) -> 'Notification':
        return cls.create(**{
            cls.user.name: user,
            cls.kind.name: kind,
            cls.message.name: message,
            cls.related_id.name: related_id,
            cls.action_url.name: action_url,
        })


@post_save(sender=Notification)
def on_notification_saved(
    model_class: Type[Notification],
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
    is_archived = BooleanField(default=False, index=True)
    due_date = DateTimeField(null=True)
    notebook_num = IntegerField(default=0)
    order = IntegerField(default=0, index=True)

    def open_for_new_solutions(self) -> bool:
        if self.due_date is None:
            return not self.is_archived
        return datetime.now() < self.due_date and not self.is_archived

    @classmethod
    def get_objects(cls, fetch_archived: bool = False):
        exercises = cls.select().order_by(Exercise.order)
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
    def to_choices(cls: enum.EnumMeta) -> Tuple[Tuple[str, str], ...]:
        choices = cast(Iterable[enum.Enum], tuple(cls))
        return tuple((choice.name, choice.value) for choice in choices)


class Solution(BaseModel):
    STATES = SolutionState
    MAX_CHECK_TIME_SECONDS = 60 * 10

    exercise = ForeignKeyField(Exercise, backref='solutions')
    solver = ForeignKeyField(User, backref='solutions')
    checker = ForeignKeyField(User, null=True, backref='solutions')
    state = CharField(
        choices=STATES.to_choices(),
        default=STATES.CREATED.name,
        index=True,
    )
    grade = IntegerField(
        default=0, constraints=[Check('grade <= 100'), Check('grade >= 0')],
    )
    submission_timestamp = DateTimeField(index=True)
    hashed = TextField()

    @property
    def solution_files(
            self,
    ) -> Union[Iterable['SolutionFile'], 'SolutionFile']:
        return SolutionFile.filter(SolutionFile.solution == self)

    @property
    def is_shared(self):
        return bool(self.shared)

    @property
    def is_checked(self):
        return self.state == self.STATES.DONE.name

    @staticmethod
    def create_hash(content: Union[str, bytes], *args, **kwargs) -> str:
        return hashing.by_content(content, *args, **kwargs)

    @classmethod
    def is_duplicate(
            cls, content: Union[str, bytes], user: User, *,
            already_hashed: bool = False,
    ) -> bool:
        hash_ = cls.create_hash(content) if not already_hashed else content
        return cls.select().where(
            cls.hashed == hash_,
            cls.solver == user,
        ).exists()

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

    def ordered_versions(self) -> Iterable['Solution']:
        return Solution.select().where(
            Solution.exercise == self.exercise,
            Solution.solver == self.solver,
        ).order_by(Solution.submission_timestamp.asc())

    def test_results(self) -> Iterable[dict]:
        return SolutionExerciseTestExecution.by_solution(self)

    @classmethod
    def of_user(
        cls, user_id: int, with_archived: bool = False,
    ) -> Iterable[Dict[str, Any]]:
        db_exercises = Exercise.get_objects(fetch_archived=with_archived)
        exercises = Exercise.as_dicts(db_exercises)

        solutions = (
            cls
            .select(cls.exercise, cls.id, cls.state, cls.checker)
            .where(cls.exercise.in_(db_exercises), cls.solver == user_id)
            .order_by(cls.submission_timestamp.desc())
        )
        for solution in solutions:
            exercise = exercises[solution.exercise_id]
            if exercise.get('solution_id') is None:
                exercise['solution_id'] = solution.id
                exercise['is_checked'] = solution.is_checked
                exercise['comments_num'] = len(solution.staff_comments)
                if solution.is_checked and solution.checker:
                    exercise['checker'] = solution.checker.fullname
        return tuple(exercises.values())

    @property
    def comments(self):
        return Comment.select().join(
            SolutionFile,
        ).where(SolutionFile.solution == self)

    @property
    def ordered_comments(self):
        return self.comments.order_by(Comment.timestamp.desc())

    @property
    def staff_comments(self):
        return self.comments.switch(Comment).join(User).join(Role).where(
            (Comment.commenter.role == Role.get_staff_role().id)
            | (Comment.commenter.role == Role.get_admin_role().id),
        )

    @property
    def comments_per_file(self):
        return Counter(c.file.id for c in self.staff_comments)

    @classmethod
    def create_solution(
        cls,
        exercise: Exercise,
        solver: User,
        files: List['File'],
        hash_: Optional[str] = None,
    ) -> 'Solution':
        if len(files) == 1:
            hash_ = cls.create_hash(files[0].code)

        if hash_ and cls.is_duplicate(hash_, solver, already_hashed=True):
            raise AlreadyExists('This solution already exists.')

        instance = cls.create(**{
            cls.exercise.name: exercise,
            cls.solver.name: solver,
            cls.submission_timestamp.name: datetime.now(),
            cls.hashed.name: hash_,
        })

        files_details = [
            {
                SolutionFile.path.name: f.path,
                SolutionFile.solution_id.name: instance.id,
                SolutionFile.code.name: f.code,
                SolutionFile.file_hash.name: SolutionFile.create_hash(f.code),
            }
            for f in files
        ]
        SolutionFile.insert_many(files_details).execute()

        # update old solutions for this exercise
        other_solutions: Iterable[Solution] = cls.select().where(
            cls.exercise == exercise,
            cls.solver == solver,
            cls.id != instance.id,
        )
        for old_solution in other_solutions:
            old_solution.set_state(Solution.STATES.OLD_SOLUTION)
        return instance

    @classmethod
    def _base_next_unchecked(cls):
        comments_count = fn.Count(Comment.id).alias('comments_count')
        fails = fn.Count(SolutionExerciseTestExecution.id).alias('failures')
        return cls.select(
            cls.id,
            cls.state,
            cls.exercise,
            comments_count,
            fails,
        ).join(
            SolutionFile,
            join_type=JOIN.LEFT_OUTER,
            on=(SolutionFile.solution == cls.id),
        ).join(
            Comment,
            join_type=JOIN.LEFT_OUTER,
            on=(Comment.file == SolutionFile.id),
        ).join(
            SolutionExerciseTestExecution,
            join_type=JOIN.LEFT_OUTER,
            on=(SolutionExerciseTestExecution.solution == cls.id),
        ).where(
            cls.state == Solution.STATES.CREATED.name,
        ).group_by(
            cls.id,
        ).order_by(
            comments_count,
            fails,
            cls.submission_timestamp.asc(),
        )

    def mark_as_checked(
        self,
        by: Optional[Union[User, int]] = None,
    ) -> bool:
        return self.set_state(
            Solution.STATES.DONE,
            checker=by,
        )

    @classmethod
    def next_unchecked(cls) -> Optional['Solution']:
        try:
            return cls._base_next_unchecked().get()
        except cls.DoesNotExist:
            return None

    @classmethod
    def next_unchecked_of(cls, exercise_id) -> Optional['Solution']:
        try:
            return cls._base_next_unchecked().where(
                cls.exercise == exercise_id,
            ).get()
        except cls.DoesNotExist:
            return None

    @classmethod
    def status(cls):
        one_if_is_checked = Case(
            Solution.state, ((Solution.STATES.DONE.name, 1),), 0,
        )
        fields = (
            Exercise.id,
            Exercise.subject.alias('name'),
            Exercise.is_archived.alias('is_archived'),
            fn.Count(Solution.id).alias('submitted'),
            fn.Sum(one_if_is_checked).alias('checked'),
        )
        join_by_exercise = (Solution.exercise == Exercise.id)
        active_solutions = Solution.state.in_(
            Solution.STATES.active_solutions(),
        )
        return (
            Exercise
            .select(*fields)
            .join(Solution, JOIN.LEFT_OUTER, on=join_by_exercise)
            .where(active_solutions)
            .group_by(Exercise.subject, Exercise.id)
            .order_by(Exercise.id)
        )

    @classmethod
    def left_in_exercise(cls, exercise: Exercise) -> int:
        one_if_is_checked = Case(
            Solution.state, ((Solution.STATES.DONE.name, 1),), 0)
        active_solutions = cls.state.in_(Solution.STATES.active_solutions())
        response = cls.filter(
            cls.exercise == exercise,
            active_solutions,
        ).select(
            fn.Count(cls.id).alias('submitted'),
            fn.Sum(one_if_is_checked).alias('checked'),
        ).dicts().get()
        return int(response['checked'] * 100 / response['submitted'])


class SolutionFile(BaseModel):
    path = TextField(default='/main.py')
    solution = ForeignKeyField(Solution, backref='files')
    code = TextField()
    file_hash = TextField()

    @classmethod
    def is_duplicate(
            cls, exercise: Exercise, solver: User, code: str,
    ) -> bool:
        return cls.select().where(
            cls.solution.exercise == Exercise,
            cls.solver == solver,
            cls.hashed == cls.create_hash(code),
        ).exists()

    @staticmethod
    def create_hash(content: Union[str, bytes], *args, **kwargs) -> str:
        return hashing.by_content(content, *args, **kwargs)

    @property
    def suffix(self) -> str:
        filename, _, ext = self.path.rpartition('.')
        return ext if filename else ''


class SharedSolution(BaseModel):
    shared_url = TextField(primary_key=True, unique=True)
    solution = ForeignKeyField(Solution, backref='shared')

    @classmethod
    def create_new(
        cls, solution: Solution,
    ) -> 'SharedSolution':
        new_url = generate_string(
            min_len=10, max_len=11, allow_punctuation=False,
        )
        exists = cls.get_or_none(cls.shared_url == new_url)
        while exists is not None:
            log.debug(
                f'Collision with creating link to {solution.id} solution, ',
                'trying again.',
            )
            new_url = generate_string(
                min_len=10, max_len=11, allow_punctuation=False,
            )
            exists = cls.get_or_none(cls.shared_url == new_url)

        return cls.create(shared_url=new_url, solution=solution)


class SharedSolutionEntry(BaseModel):
    referrer = TextField(null=True)
    time = DateTimeField(default=datetime.now())
    user = ForeignKeyField(User, backref='entries')
    shared_solution = ForeignKeyField(SharedSolution, backref='entries')


class ExerciseTest(BaseModel):
    exercise = ForeignKeyField(model=Exercise, unique=True)
    code = TextField()

    @classmethod
    def get_or_create_exercise_test(cls, exercise: Exercise, code: str):
        instance, created = cls.get_or_create(**{
            cls.exercise.name: exercise,
        }, defaults={
            cls.code.name: code,
        })
        if not created:
            instance.code = code
            instance.save()
        return instance

    @classmethod
    def get_by_exercise(cls, exercise: Exercise):
        return cls.get_or_none(cls.exercise == exercise)


class ExerciseTestName(BaseModel):
    FATAL_TEST_NAME = 'fatal_test_failure'
    FATAL_TEST_PRETTY_TEST_NAME = _('כישלון חמור')

    exercise_test = ForeignKeyField(model=ExerciseTest)
    test_name = TextField()
    pretty_test_name = TextField()

    indexes = (
        (('exercise_test', 'test_name'), True),
    )

    @classmethod
    def create_exercise_test_name(
        cls,
        exercise_test: ExerciseTest,
        test_name: str,
        pretty_test_name: str,
    ):
        instance, created = cls.get_or_create(**{
            cls.exercise_test.name: exercise_test,
            cls.test_name.name: test_name,
        }, defaults={
            cls.pretty_test_name.name: pretty_test_name,
        })
        if not created:
            instance.pretty_test_name = pretty_test_name
            instance.save()

    @classmethod
    def get_exercise_test(cls, exercise: Exercise, test_name: str):
        if test_name == cls.FATAL_TEST_NAME:
            instance, _ = cls.get_or_create(**{
                cls.exercise_test.name: ExerciseTest.get_by_exercise(exercise),
                cls.test_name.name: test_name,
            }, defaults={
                cls.pretty_test_name.name: cls.FATAL_TEST_PRETTY_TEST_NAME,
            })
            return instance
        instance, _ = cls.get_or_create(**{
            cls.exercise_test.name: ExerciseTest.get_by_exercise(exercise),
            cls.test_name.name: test_name,
        }, defaults={
            cls.pretty_test_name.name: test_name,
        })
        return instance


class SolutionExerciseTestExecution(BaseModel):
    solution = ForeignKeyField(model=Solution)
    exercise_test_name = ForeignKeyField(model=ExerciseTestName)
    user_message = TextField()
    staff_message = TextField()

    @classmethod
    def create_execution_result(
        cls,
        solution: Solution,
        test_name: str,
        user_message: str,
        staff_message: str,
    ):
        exercise_test_name = ExerciseTestName.get_exercise_test(
            exercise=solution.exercise,
            test_name=test_name,
        )
        cls.create(**{
            cls.solution.name: solution,
            cls.exercise_test_name.name: exercise_test_name,
            cls.user_message.name: user_message,
            cls.staff_message.name: staff_message,
        })

    @classmethod
    def by_solution(cls, solution: Solution) -> Iterable[dict]:
        return cls.filter(
            cls.solution == solution,
        ).join(ExerciseTestName).select(
            ExerciseTestName.pretty_test_name,
            cls.user_message,
            cls.staff_message,
        ).dicts()


class CommentText(BaseModel):
    text = TextField(unique=True)
    flake8_key = TextField(null=True)

    @classmethod
    def create_comment(
        cls, text: str, flake_key: Optional[str] = None,
    ) -> 'CommentText':
        instance, _ = CommentText.get_or_create(
            **{CommentText.text.name: html.escape(text)},
            defaults={CommentText.flake8_key.name: flake_key},
        )
        return instance


class Comment(BaseModel):
    commenter = ForeignKeyField(User, backref='comments')
    timestamp = DateTimeField(default=datetime.now)
    line_number = IntegerField(constraints=[Check('line_number >= 1')])
    comment = ForeignKeyField(CommentText)
    file = ForeignKeyField(SolutionFile, backref='comments')
    is_auto = BooleanField(default=False)

    @classmethod
    def by_solution(
            cls,
            solution: Solution,
    ) -> Union[Iterable['Comment'], 'Comment']:
        return cls.select().join(
            SolutionFile,
        ).filter(SolutionFile.solution == solution)

    @property
    def solution(self) -> Solution:
        return self.file.solution

    @classmethod
    def create_comment(
        cls,
        commenter: User,
        line_number: int,
        comment_text: CommentText,
        file: SolutionFile,
        is_auto: bool,
    ) -> 'Comment':
        return cls.get_or_create(
            commenter=commenter,
            line_number=line_number,
            comment=comment_text,
            file=file,
            is_auto=is_auto,
        )

    @classmethod
    def _by_file(cls, file_id: int):
        fields = (
            cls.id, cls.line_number, cls.is_auto,
            CommentText.id.alias('comment_id'), CommentText.text,
            SolutionFile.id.alias('file_id'),
            User.fullname.alias('author_name'),
            User.role.alias('author_role'),
        )
        return (
            cls
            .select(*fields)
            .join(SolutionFile)
            .switch()
            .join(CommentText)
            .switch()
            .join(User)
            .where(cls.file == file_id)
            .order_by(cls.timestamp.asc())
        )

    @classmethod
    def by_file(cls, file_id: int) -> Tuple[Dict[Any, Any], ...]:
        return tuple(cls._by_file(file_id).dicts())


def generate_string(
    min_len: int = 9, max_len: int = 16, allow_punctuation: bool = True,
) -> str:
    randomizer = secrets.SystemRandom()
    length = randomizer.randrange(min_len, max_len)
    if allow_punctuation:
        password = randomizer.choices(string.printable[:66], k=length)
    else:
        password = randomizer.choices(
            string.ascii_letters + string.digits, k=length,
        )
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
        password = User.random_password()
        api_key = User.random_password(stronger=True)
        User.create(**user, password=password, api_key=api_key)
        print(f"User: {user['username']}, Password: {password}")  # noqa: T001


def create_basic_roles():
    for role in RoleOptions:
        Role.create(name=role.value)


ALL_MODELS = BaseModel.__subclasses__()
