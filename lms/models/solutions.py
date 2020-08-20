from operator import itemgetter
from typing import Any, Dict, Iterable, List, Optional

from lms.lmsdb.models import Solution, SolutionFile
from lms.lmstests.public.general import tasks as general_tasks
from lms.lmstests.public.identical_tests import tasks as identical_tests_tasks
from lms.lmsweb import config, routes
from lms.models import notifications


def mark_as_checked(solution_id: int, checker_id: int) -> bool:
    checked_solution: Solution = Solution.get_by_id(solution_id)
    is_updated = checked_solution.mark_as_checked(by=checker_id)
    msg = f'הפתרון שלך לתרגיל "{checked_solution.exercise.subject}" נבדק.'
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
