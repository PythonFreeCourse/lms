from io import BytesIO
from lms.extractors.base import File
from operator import itemgetter
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
from zipfile import ZipFile

from flask_babel import gettext as _

from lms.lmsdb.models import Solution, SolutionFile, User
from lms.lmstests.public.general import tasks as general_tasks
from lms.lmstests.public.identical_tests import tasks as identical_tests_tasks
from lms.lmsweb import config, routes
from lms.models import notifications


def notify_comment_after_check(user: User, solution: Solution) -> bool:
    is_checked = solution.is_checked
    if is_checked:
        msg, addressee = get_message_and_addressee(user, solution)
        if check_notify_after_comment(user, solution):
            notifications.send(
                kind=notifications.NotificationKind.USER_RESPONSE,
                user=addressee,
                related_id=solution.id,
                message=msg,
                action_url=f'{routes.SOLUTIONS}/{solution.id}',
            )
            return True
    return False


def check_notify_after_comment(user: User, solution: Solution) -> bool:
    return (
        not solution.comments
        or (
            solution.comments
            and not solution.ordered_comments[0].commenter == user
        )
    )


def get_message_and_addressee(
    user: User, solution: Solution,
) -> Tuple[str, User]:
    if solution.solver == user:
        msg = _(
            '%(solver)s הגיב לך על בדיקת תרגיל "%(subject)s".',
            solver=solution.solver.fullname,
            subject=solution.exercise.subject,
        )
        addressee = solution.checker
    else:  # solution.checker == user
        msg = _(
            '%(checker)s הגיב לך על תרגיל "%(subject)s".',
            checker=solution.checker.fullname,
            subject=solution.exercise.subject,
        )
        addressee = solution.solver
    return msg, addressee


def mark_as_checked(solution_id: int, checker_id: int) -> bool:
    checked_solution: Solution = Solution.get_by_id(solution_id)
    is_updated = checked_solution.mark_as_checked(by=checker_id)
    msg = _(
        'הפתרון שלך לתרגיל "%(subject)s" נבדק.',
        subject=checked_solution.exercise.subject,
    )
    if is_updated:
        notifications.send(
            kind=notifications.NotificationKind.CHECKED,
            user=checked_solution.solver,
            related_id=solution_id,
            message=msg,
            action_url=f'{routes.SOLUTIONS}/{solution_id}',
        )
    if config.FEATURE_FLAG_CHECK_IDENTICAL_CODE_ON:
        (identical_tests_tasks.check_if_other_solutions_can_be_solved.
         apply_async(args=(solution_id,)))
    return is_updated


def get_next_unchecked(exercise_id: int = 0) -> Optional[Solution]:
    if exercise_id == 0:
        return Solution.next_unchecked()
    return Solution.next_unchecked_of(exercise_id)


def start_checking(solution: Optional[Solution]) -> bool:
    if solution and solution.start_checking():
        general_tasks.reset_solution_state_if_needed.apply_async(
            args=(solution.id,),
            countdown=Solution.MAX_CHECK_TIME_SECONDS,
        )
        return True
    return False


def create_zip_from_solution(
    files: Iterable[Union[SolutionFile, File]],
) -> bytes:
    with BytesIO() as memory_file:
        with ZipFile(memory_file, 'w') as archive:
            for file in files:
                if not file.path.endswith(os.path.sep):
                    archive.writestr(file.path.strip(os.path.sep), file.code)
        memory_file.seek(0)
        return memory_file.read()


def get_files_tree(files: Iterable[SolutionFile]) -> List[Dict[str, Any]]:
    file_details = [
        {
            'id': file.id,
            'fullpath': file.path,
            'path': file.path.strip('/').rpartition('/')[2],
            'indent': file.path.strip('/').count('/'),
            'is_folder': file.path.endswith('/'),
            'code': file.code,
        }
        for file in files
    ]
    file_details.sort(key=itemgetter('fullpath'))
    for file in file_details:
        del file['fullpath']
    return file_details
