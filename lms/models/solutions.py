from io import BytesIO
import os
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, Union
from zipfile import ZipFile

from flask_babel import gettext as _  # type: ignore
from flask_login import current_user  # type: ignore
from playhouse.shortcuts import model_to_dict  # type: ignore

from lms.extractors.base import File
from lms.lmsdb.models import (
    SharedSolution, Solution, SolutionAssessment, SolutionFile, User,
)
from lms.lmstests.public.general import tasks as general_tasks
from lms.lmstests.public.identical_tests import tasks as identical_tests_tasks
from lms.lmsweb import config, routes
from lms.models import comments, notifications
from lms.models.errors import ForbiddenPermission, ResourceNotFound
from lms.utils.files import ALLOWED_IMAGES_EXTENSIONS


def notify_comment_after_check(user: User, solution: Solution) -> bool:
    is_checked = solution.is_checked
    if is_checked:
        msg, addressee = get_message_and_addressee(user, solution)
        if is_last_to_reply(user, solution):
            notifications.send(
                kind=notifications.NotificationKind.USER_RESPONSE,
                user=addressee,
                related_id=solution.id,
                message=msg,
                action_url=f'{routes.SOLUTIONS}/{solution.id}',
            )
            return True
    return False


def is_last_to_reply(user: User, solution: Solution) -> bool:
    return (
        not solution.comments
        or (
            solution.comments
            and solution.ordered_comments[0].commenter != user
        )
    )


def get_message_and_addressee(
    user: User, solution: Solution,
) -> Tuple[str, User]:
    if solution.solver == user:
        msg = _(
            '%(solver)s has replied for your "%(subject)s" check.',
            solver=solution.solver.fullname,
            subject=solution.exercise.subject,
        )
        addressee = solution.checker
    else:  # solution.checker == user
        msg = _(
            '%(checker)s replied for "%(subject)s".',
            checker=solution.checker.fullname,
            subject=solution.exercise.subject,
        )
        addressee = solution.solver
    return msg, addressee


def change_assessment(
    solution_id: int, assessment_id: Optional[int] = None,
) -> bool:
    checked_solution: Solution = Solution.get_by_id(solution_id)
    return checked_solution.change_assessment(assessment_id=assessment_id)


def mark_as_checked(solution_id: int, checker_id: int) -> bool:
    checked_solution: Solution = Solution.get_by_id(solution_id)
    is_updated = checked_solution.mark_as_checked(by=checker_id)
    msg = _(
        'Your solution for the "%(subject)s" exercise has been checked.',
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


def get_view_parameters(
    solution: Solution, file_id: Optional[int], shared_url: str,
    is_manager: bool, solution_files: Tuple[SolutionFile, ...],
    viewer_is_solver: bool,
) -> Dict[str, Any]:
    versions = solution.ordered_versions()
    test_results = solution.test_results()
    files = get_files_tree(solution.files)
    file_id = file_id or (files[0]['id'] if files else None)
    file_to_show = next((f for f in solution_files if f.id == file_id), None)
    if file_to_show is None:
        raise ResourceNotFound('File does not exist.', 404)

    view_params = {
        'solution': model_to_dict(solution),
        'files': files,
        'comments': solution.comments_per_file,
        'current_file': file_to_show,
        'is_manager': is_manager,
        'role': current_user.role.name.lower(),
        'versions': versions,
        'test_results': test_results,
        'shared_url': shared_url,
        'image_extensions': ALLOWED_IMAGES_EXTENSIONS,
    }

    if is_manager:
        view_params = {
            **view_params,
            'exercise_common_comments':
                comments._common_comments(exercise_id=solution.exercise),
            'left': Solution.left_in_exercise(solution.exercise),
            'assessments':
                SolutionAssessment.get_assessments(solution.exercise.course),
        }

    if viewer_is_solver:
        notifications.read_related(solution.id, current_user.id)

    return view_params


def get_download_data(
    download_id: str,
) -> Tuple[Iterator[SolutionFile], str]:
    solution = Solution.get_or_none(Solution.id == download_id)
    shared_solution = SharedSolution.get_or_none(
        SharedSolution.shared_url == download_id,
    )
    if solution is None and shared_solution is None:
        raise ResourceNotFound('Solution does not exist.', 404)

    if shared_solution is None:
        viewer_is_solver = solution.solver.id == current_user.id
        has_viewer_access = current_user.role.is_viewer
        if not viewer_is_solver and not has_viewer_access:
            raise ForbiddenPermission(
                'This user has no permissions to view this page.', 403,
            )
        files = solution.files
        filename = solution.exercise.subject
    else:
        files = shared_solution.solution.files
        filename = shared_solution.solution.exercise.subject

    return files, filename


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


def order_files(file: Dict[str, Any]) -> Tuple[str, bool]:
    return (
        os.path.split(file['fullpath'])[0],
        not file['is_folder'],  # folders should be before the files
    )


def get_files_tree(files: Iterable[SolutionFile]) -> List[Dict[str, Any]]:
    file_details = [
        {
            'id': file.id,  # type: ignore
            'fullpath': file.path,
            'path': os.path.split(file.path.strip('/'))[1],  # type: ignore
            'indent': file.path.strip('/').count('/'),  # type: ignore
            'is_folder': file.path.endswith('/'),
            'code': file.code,
        }
        for file in files
    ]
    file_details.sort(key=order_files)
    for file in file_details:
        del file['fullpath']
    return file_details
