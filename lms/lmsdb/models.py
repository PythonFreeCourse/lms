import enum
import html
import secrets
import string
from collections import Counter
from datetime import datetime
from typing import (
    Any, Dict, Iterable, List, Optional,
    TYPE_CHECKING, Tuple, Type, Union, cast,
)
from uuid import uuid4

from flask_babel import gettext as _  # type: ignore
from flask_login import UserMixin, current_user  # type: ignore
from peewee import (  # type: ignore
    BooleanField, Case, CharField, Check, DateTimeField, ForeignKeyField,
    IntegerField, JOIN, ManyToManyField, TextField, UUIDField, fn,
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
    UNVERIFIED = 'Unverified'
    STUDENT = 'Student'
    STAFF = 'Staff'
    VIEWER = 'Viewer'
    ADMINISTRATOR = 'Administrator'

    def __str__(self):
        return self.value


class NotePrivacy(enum.IntEnum):
    PRIVATE = 40
    STAFF = 30
    USER = 20
    PUBLIC = 10

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
        (RoleOptions.UNVERIFIED.value, RoleOptions.UNVERIFIED.value),
        (RoleOptions.BANNED.value, RoleOptions.BANNED.value),
    ))

    def __str__(self):
        return self.name

    @classmethod
    def get_banned_role(cls) -> 'Role':
        return cls.get(Role.name == RoleOptions.BANNED.value)

    @classmethod
    def get_unverified_role(cls) -> 'Role':
        return cls.get(Role.name == RoleOptions.UNVERIFIED.value)

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
    def is_unverified(self) -> bool:
        return self.name == RoleOptions.UNVERIFIED.value

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


class Course(BaseModel):
    name = CharField(unique=True)
    date = DateTimeField(default=datetime.now)
    end_date = DateTimeField(null=True)
    close_registration_date = DateTimeField(default=datetime.now)
    invite_code = CharField(null=True)
    is_public = BooleanField(default=False)

    def has_user(self, user_id: int) -> bool:
        return UserCourse.is_user_registered(user_id, self)

    @classmethod
    def fetch(cls, user: 'User') -> Iterable['Course']:
        return (
            cls
            .select()
            .join(UserCourse)
            .where(UserCourse.user == user.id)
            .order_by(Course.name.desc())
        )

    def __str__(self):
        return f'{self.name}: {self.date} - {self.end_date}'


class User(UserMixin, BaseModel):
    username = CharField(unique=True)
    fullname = CharField()
    mail_address = CharField(unique=True)
    password = CharField()
    role = ForeignKeyField(Role, backref='users')
    api_key = CharField()
    last_course_viewed = ForeignKeyField(Course, null=True)
    uuid = UUIDField(default=uuid4, unique=True)

    def get_id(self):
        return str(self.uuid)

    def is_password_valid(self, password) -> bool:
        return check_password_hash(self.password, password)

    def has_course(self, course_id: int) -> bool:
        return UserCourse.is_user_registered(self, course_id)

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

    def get_courses(self) -> Iterable['Course']:
        return Course.fetch(self)

    def notes(self) -> Iterable['Note']:
        fields = (
            Note.id, Note.creator.fullname, CommentText.text,
            Note.timestamp, Note.exercise.subject, Note.privacy,
        )
        public_or_mine = (
            (Note.privacy != NotePrivacy.PRIVATE.value)
            | (Note.creator == current_user.id)
        )

        notes = (
            Note
            .select(*fields)
            .join(User, on=(Note.creator == User.id))
            .switch()
            .join(Exercise, join_type=JOIN.LEFT_OUTER)
            .switch()
            .join(CommentText)
            .switch()
            .where((Note.user == self) & (public_or_mine))
        )
        if not current_user.role.is_manager:
            notes = notes.where(Note.privacy <= NotePrivacy.USER.value)

        return notes

    def __str__(self):
        return f'{self.username} - {self.fullname}'


@pre_save(sender=User)
def on_save_handler(model_class, instance, created):
    """Hash password on creation/save."""

    # If password changed then it won't start with hash's method prefix
    is_password_changed = not instance.password.startswith('pbkdf2:sha256')
    if created or is_password_changed:
        instance.password = generate_password_hash(instance.password)
        instance.uuid = uuid4()

    is_api_key_changed = not instance.api_key.startswith('pbkdf2:sha256')
    if created or is_api_key_changed:
        if not instance.api_key:
            instance.api_key = model_class.random_password()
        instance.api_key = generate_password_hash(instance.api_key)


class UserCourse(BaseModel):
    user = ForeignKeyField(User, backref='usercourses')
    course = ForeignKeyField(Course, backref='usercourses')
    date = DateTimeField(default=datetime.now)

    @classmethod
    def is_user_registered(cls, user_id: int, course_id: int) -> bool:
        return (
            cls.
            select()
            .where(
                cls.user == user_id,
                cls.course == course_id,
            )
            .exists()
        )


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
    course = ForeignKeyField(Course, backref='exercise')
    number = IntegerField(default=1)

    class Meta:
        indexes = (
            (('course_id', 'number'), True),
        )

    def open_for_new_solutions(self) -> bool:
        if self.due_date is None:
            return not self.is_archived
        return datetime.now() < self.due_date and not self.is_archived

    @classmethod
    def get_highest_number(cls):
        return cls.select(fn.MAX(cls.number)).scalar()

    @classmethod
    def is_number_exists(cls, number: int) -> bool:
        return cls.select().where(cls.number == number).exists()

    @classmethod
    def get_objects(
        cls, user_id: int, fetch_archived: bool = False,
        from_all_courses: bool = False,
    ):
        user = User.get(User.id == user_id)
        exercises = (
            cls
            .select()
            .join(Course)
            .join(UserCourse)
            .where(UserCourse.user == user_id)
            .switch()
            .order_by(UserCourse.date, Exercise.number, Exercise.order)
        )
        if not from_all_courses:
            exercises = exercises.where(
                UserCourse.course == user.last_course_viewed,
            )
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
            'exercise_number': self.number,
            'course_id': self.course.id,
            'course_name': self.course.name,
        }

    @staticmethod
    def as_dicts(exercises: Iterable['Exercise']) -> ExercisesDictById:
        return {exercise.id: exercise.as_dict() for exercise in exercises}

    def __str__(self):
        return self.subject


@pre_save(sender=Exercise)
def exercise_number_save_handler(model_class, instance, created):
    """Change the exercise number to the highest consecutive number."""

    if model_class.is_number_exists(instance.number):
        instance.number = model_class.get_highest_number() + 1


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


class SolutionStatusView(enum.Enum):
    UPLOADED = 'Uploaded'
    NOT_CHECKED = 'Not checked'
    CHECKED = 'Checked'

    @classmethod
    def to_choices(cls: enum.EnumMeta) -> Tuple[Tuple[str, str], ...]:
        choices = cast(Iterable[enum.Enum], tuple(cls))
        return tuple((choice.name, choice.value) for choice in choices)


class Solution(BaseModel):
    STATES = SolutionState
    STATUS_VIEW = SolutionStatusView
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
    last_status_view = CharField(
        choices=STATUS_VIEW.to_choices(),
        default=STATUS_VIEW.UPLOADED.name,
        index=True,
    )
    last_time_view = DateTimeField(default=datetime.now, null=True, index=True)

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
            cls, content: Union[str, bytes], user: User, exercise: Exercise,
            *, already_hashed: bool = False,
    ) -> bool:

        hash_ = cls.create_hash(content) if not already_hashed else content

        last_submission_hash = (
            cls
            .select(cls.hashed)
            .where(
                cls.exercise == exercise,
                cls.solver == user,
            )
            .order_by(cls.submission_timestamp.desc())
            .limit(1)
            .scalar()
        )

        return last_submission_hash == hash_

    def view_solution(self) -> None:
        self.last_time_view = datetime.now()
        if (
            self.last_status_view != self.STATUS_VIEW.NOT_CHECKED.name
            and self.state == self.STATES.CREATED.name
        ):
            self.last_status_view = self.STATUS_VIEW.NOT_CHECKED.name
        elif (
            self.last_status_view != self.STATUS_VIEW.CHECKED.name
            and self.state == self.STATES.DONE.name
        ):
            self.last_status_view = self.STATUS_VIEW.CHECKED.name
        self.save()

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
        return changes.execute() == 1

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
        from_all_courses: bool = False,
    ) -> Iterable[Dict[str, Any]]:
        db_exercises = Exercise.get_objects(
            user_id=user_id, fetch_archived=with_archived,
            from_all_courses=from_all_courses,
        )
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

        if (
            hash_
            and cls.is_duplicate(hash_, solver, exercise, already_hashed=True)
        ):
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
    FATAL_TEST_PRETTY_TEST_NAME = _('Fatal error')

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


class Note(BaseModel):
    creator = ForeignKeyField(User)
    user = ForeignKeyField(User)
    timestamp = DateTimeField(default=datetime.now())
    note = ForeignKeyField(CommentText)
    exercise = ForeignKeyField(Exercise, null=True)
    privacy = IntegerField(choices=(
        (NotePrivacy.PRIVATE.value, NotePrivacy.PRIVATE.value),
        (NotePrivacy.STAFF.value, NotePrivacy.STAFF.value),
        (NotePrivacy.USER.value, NotePrivacy.USER.value),
        (NotePrivacy.PUBLIC.value, NotePrivacy.PUBLIC.value),
    ))

    @property
    def is_private(self) -> bool:
        return self.privacy == NotePrivacy.PRIVATE.value

    @property
    def is_staff(self) -> bool:
        return self.privacy == NotePrivacy.STAFF.value

    @property
    def is_solver(self) -> bool:
        return self.privacy == NotePrivacy.USER.value

    @property
    def is_public(self) -> bool:
        return self.privacy == NotePrivacy.PUBLIC.value

    @staticmethod
    def get_note_options():
        return ','.join(option.name.capitalize() for option in NotePrivacy)

    @staticmethod
    def get_privacy_level(level: int) -> NotePrivacy:
        return list(NotePrivacy)[level].value


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


def create_demo_users() -> None:
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


def create_basic_roles() -> None:
    for role in RoleOptions:
        Role.create(name=role.value)


def create_basic_course() -> Course:
    return Course.create(name='Python Course', date=datetime.now())


ALL_MODELS = BaseModel.__subclasses__()
