import json
import os
from functools import wraps
from typing import Optional
from urllib.parse import urljoin, urlparse

from flask import (
    abort, jsonify, render_template, request, send_from_directory, url_for,
)
from flask_admin import Admin, AdminIndexView  # type: ignore
from flask_admin.contrib.peewee import ModelView  # type: ignore
from flask_login import (  # type: ignore
    LoginManager, current_user, login_required, login_user, logout_user,
)
from peewee import fn  # type: ignore
from playhouse.shortcuts import model_to_dict  # type: ignore
from werkzeug.datastructures import FileStorage
from werkzeug.utils import redirect

from lms.lmsdb.models import (
    ALL_MODELS, Comment, CommentText, Exercise, RoleOptions, Solution, User,
    database,
)
from lms import notifications
from lms.lmstests.public.flake8 import tasks as flake8_tasks
from lms.lmstests.public.general import tasks as general_tasks
from lms.lmstests.public.identical_tests import tasks as identical_tests_tasks
from lms.lmsweb import webapp
from lms.lmsweb.tools.notebook_extractor import extract_exercises

login_manager = LoginManager()
login_manager.init_app(webapp)
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'

PERMISSIVE_CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,PUT,POST,DELETE',
}

HIGH_ROLES = {str(RoleOptions.STAFF), str(RoleOptions.ADMINISTRATOR)}
MAX_REQUEST_SIZE = 550_000  # 550 KB


@webapp.before_request
def _db_connect():
    database.connect()


@webapp.after_request
def after_request(response):
    for name, value in PERMISSIVE_CORS.items():
        response.headers.add(name, value)
    return response


@webapp.teardown_request
def _db_close(exc):
    if not database.is_closed():
        database.close()


@login_manager.user_loader
def load_user(user_id):
    return User.get_or_none(id=user_id)


def managers_only(func):
    # Must have @wraps to work with endpoints.
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.role.is_manager:
            return fail(403, 'This user has no permissions to view this page.')
        else:
            return func(*args, **kwargs)

    return wrapper


def fail(status_code: int, error_msg: str):
    data = {
        'status': 'failed',
        'msg': error_msg,
    }
    response = jsonify(data)
    response.status_code = status_code
    return abort(response)


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return (
        test_url.scheme in ('http', 'https')
        and ref_url.netloc == test_url.netloc
    )


@webapp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main'))

    username = request.form.get('username')
    password = request.form.get('password')
    user = User.get_or_none(username=username)

    if user is not None and user.is_password_valid(password):
        login_user(user)
        next_url = request.args.get('next_url')
        if not is_safe_url(next_url):
            return fail(400, "The URL isn't safe.")
        return redirect(next_url or url_for('main'))

    return render_template('login.html')


@webapp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('login')


@webapp.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(webapp.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon',
    )


@webapp.route('/')
@login_required
def main():
    return redirect(url_for('exercises_page'))


@webapp.route('/status')
@managers_only
@login_required
def status():
    return render_template(
        'status.html',
        exercises=Solution.status(),
    )


@webapp.route('/exercises')
@login_required
def exercises_page():
    fetch_archived = bool(request.args.get('archived'))
    exercises = Solution.of_user(current_user.id, fetch_archived)
    is_manager = current_user.role.is_manager
    return render_template(
        'exercises.html',
        exercises=exercises,
        is_manager=is_manager,
        fetch_archived=fetch_archived,
    )


def _create_comment(
    user_id: int,
    solution: Solution,
    kind: str,
    line_number: int,
    comment_text: Optional[str] = None,  # set when kind == text
    comment_id: Optional[int] = None,  # set when kind == id
):
    user = User.get_or_none(User.id == user_id)
    if user is None:
        # should never happen, we checked session_id == solver_id
        return fail(404, 'No such user')

    if (not kind) or (kind not in ('id', 'text')):
        return fail(400, 'Invalid kind')

    if line_number <= 0:
        return fail(422, f'Invalid line number: {line_number}')

    if kind == 'id':
        new_comment_id = comment_id
    elif kind == 'text':
        if not comment_text:
            return fail(422, 'Empty comments are not allowed')
        new_comment_id = CommentText.create_comment(text=comment_text).id
    else:
        # should never happend, kind was checked before
        return fail(400, 'Invalid kind')

    comment_ = Comment.create(
        commenter=user,
        line_number=line_number,
        comment=new_comment_id,
        solution=solution,
    )

    return jsonify({
        'success': 'true', 'id': comment_.id, 'text': comment_.comment.text,
    })


@webapp.route('/notifications', methods=['GET', 'POST'])
@login_required
def get_notifications():
    if request.method == 'POST':
        if request.json:
            explicit_id = int(request.json.get('notificationId', 0))
        else:
            explicit_id = 0
        changed = notifications.mark_as_read(
            from_user=current_user, notification_id=explicit_id)
        if not changed:
            return fail(401, 'Invalid notification')
        return jsonify({'success': True})

    # it's a GET
    response = notifications.get_notifications_for_user(current_user)
    return jsonify(response)


@webapp.route('/comments', methods=['GET', 'POST'])
@login_required
def comment():
    act = request.args.get('act') or request.json.get('act')

    if request.method == 'POST':
        solution_id = int(request.json.get('solutionId', 0))
    else:  # it's a GET
        solution_id = int(request.args.get('solutionId', 0))

    solution = Solution.get_or_none(Solution.id == solution_id)
    if solution is None:
        return fail(404, f'No such solution {solution_id}')

    solver_id = solution.solver.id
    if solver_id != current_user.id and not current_user.role.is_manager:
        return fail(401, "You aren't allowed to watch this page.")

    if act == 'fetch':
        return jsonify(Comment.get_solutions(solution_id))

    if act == 'delete':
        comment_id = int(request.args.get('commentId'))
        comment_ = Comment.get_or_none(Comment.id == comment_id)
        if comment_ is not None:
            comment_.delete_instance()
        return jsonify({'success': 'true'})

    if act == 'create':
        kind = request.json.get('kind', '')
        comment_id, comment_text = None, None
        try:
            line_number = int(request.json.get('line', 0))
        except ValueError:
            line_number = 0
        if kind.lower() == 'id':
            comment_id = int(request.json.get('comment', 0))
        if kind.lower() == 'text':
            comment_text = request.json.get('comment', '')
        return _create_comment(
            current_user.id,
            solution,
            kind,
            line_number,
            comment_text,
            comment_id,
        )

    return fail(400, f'Unknown or unset act value "{act}"')


@webapp.route('/send/<int:_exercise_id>')
@login_required
def send(_exercise_id):
    return render_template('upload.html')


@webapp.route('/send', methods=['GET'])
@login_required
def send_():
    return render_template('upload.html')


@webapp.route('/upload', methods=['POST'])
@login_required
def upload():
    user_id = current_user.id
    user = User.get_or_none(User.id == user_id)  # should never happen
    if user is None:
        return fail(404, 'user not found')
    if request.content_length > MAX_REQUEST_SIZE:
        return fail(413, 'File is too heavy. 500KB allowed')

    file: FileStorage = request.files.get('file')
    if not file:
        return fail(422, 'No file was given')

    json_file_data = file.read()
    try:
        file_content = json.loads(json_file_data)
        exercises = list(extract_exercises(file_content))
    except (ValueError, json.JSONDecodeError):
        return fail(422, 'Invalid file format - must be ipynb')
    if not exercises:
        msg = 'No exercises were found in the notebook'
        desc = 'did you use Upload <number of exercise> ? (example: Upload 1)'
        return fail(422, f'{msg}, {desc}')
    matches, misses = set(), set()
    for exercise_id, code in exercises:
        exercise = Exercise.get_or_none(Exercise.id == exercise_id)
        if exercise is None:
            misses.add(exercise_id)
            continue
        if not exercise.open_for_new_solutions():
            misses.add(exercise_id)
            continue

        if Solution.solution_exists(
                exercise=exercise,
                solver=user,
                json_data_str=code,
        ):
            continue
        solution = Solution.create_solution(
            exercise=exercise,
            solver=user,
            json_data_str=code,
        )
        flake8_tasks.run_flake8_on_solution.apply_async(args=(solution.id,))
        identical_tests_tasks.solve_solution_with_identical_code.apply_async(
            args=(solution.id,))
        matches.add(exercise_id)
    return jsonify({
        'exercise_matches': list(matches),
        'exercise_misses': list(misses),
    })


@webapp.route('/view/<int:solution_id>')
@login_required
def view(solution_id):
    solution = Solution.get_or_none(Solution.id == solution_id)
    if solution is None:
        return fail(404, 'Solution does not exist.')

    is_manager = current_user.role.is_manager
    if solution.solver.id != current_user.id and not is_manager:
        return fail(403, 'This user has no permissions to view this page.')

    versions = solution.ordered_versions()
    view_params = {
        'solution': model_to_dict(solution),
        'is_manager': is_manager,
        'role': current_user.role.name.lower(),
        'versions': versions,
    }

    if is_manager:
        view_params = {
            **view_params,
            'exercise_common_comments':
                _common_comments(exercise_id=solution.exercise),
            'all_common_comments':
                _common_comments(),
            'user_comments':
                _common_comments(user_id=current_user.id),
        }

    return render_template('view.html', **view_params)


@webapp.route('/checked/<int:exercise_id>/<int:solution_id>', methods=['POST'])
@login_required
@managers_only
def done_checking(exercise_id, solution_id):
    checked_solution: Solution = Solution.get_by_id(solution_id)
    is_updated = checked_solution.set_state(new_state=Solution.STATES.DONE)
    if is_updated:
        notifications.create_notification(
            notification_type=(notifications.SolutionCheckedNotification
                               .notification_type()),
            for_user=checked_solution.solver,
            solution=checked_solution,
        )
    identical_tests_tasks.check_if_other_solutions_can_be_solved.apply_async(
        args=(solution_id,))
    next_exercise = None
    solution = Solution.next_unchecked_of(exercise_id)
    if solution and solution.start_checking():
        general_tasks.reset_solution_state_if_needed.apply_async(
            args=(solution.id,),
            countdown=Solution.MAX_CHECK_TIME_SECONDS,
        )
        next_exercise = solution.id
    return jsonify({'success': is_updated, 'next': next_exercise})


@webapp.route('/check/<int:exercise_id>')
@login_required
@managers_only
def start_checking(exercise_id):
    if exercise_id != 0:
        next_exercise = Solution.next_unchecked_of(exercise_id)
    else:
        next_exercise = Solution.next_unchecked()
    if next_exercise and next_exercise.start_checking():
        general_tasks.reset_solution_state_if_needed.apply_async(
            args=(next_exercise.id,),
            countdown=Solution.MAX_CHECK_TIME_SECONDS,
        )
        return redirect(f'/view/{next_exercise.id}')
    return redirect('/exercises')


def _common_comments(exercise_id=None, user_id=None):
    """
    Most common comments throughout all exercises.
    Filter by exercise id when specified.
    """
    query = CommentText.filter(**{
        CommentText.flake8_key.name: None,
    }).select(CommentText.id, CommentText.text).join(Comment)
    if exercise_id is not None:
        query = (query
                 .join(Solution)
                 .join(Exercise)
                 .where(Exercise.id == exercise_id)
                 )
    if user_id is not None:
        query = (query
                 .filter(Comment.commenter == user_id)
                 )

    query = (query
             .group_by(CommentText.id)
             .order_by(fn.Count(CommentText.id).desc())
             .limit(5)
             )

    return tuple(query.dicts())


@webapp.route('/common_comments')
@webapp.route('/common_comments/<exercise_id>')
@login_required
@managers_only
def common_comments(exercise_id=None):
    return jsonify(_common_comments(exercise_id=exercise_id))


class AccessibleByAdminMixin:
    def is_accessible(self):
        return (
            current_user.is_authenticated
            and current_user.role.is_administrator
        )


class MyAdminIndexView(AccessibleByAdminMixin, AdminIndexView):
    pass


class AdminModelView(AccessibleByAdminMixin, ModelView):
    pass


class AdminSolutionView(AdminModelView):
    column_filters = (
        Solution.state.name,
    )
    column_choices = {
        Solution.state.name: Solution.STATES.to_choices(),
    }


class AdminCommentView(AdminModelView):
    column_filters = (
        Comment.timestamp.name,
        Comment.is_auto.name,
    )


class AdminCommentTextView(AdminModelView):
    column_filters = (
        CommentText.text.name,
        CommentText.flake8_key.name,
    )


SPECIAL_MAPPING = {
    Solution: AdminSolutionView,
    Comment: AdminCommentView,
    CommentText: AdminCommentTextView,
}

admin = Admin(
    webapp,
    name='LMS',
    template_mode='bootstrap3',
    index_view=MyAdminIndexView(),
)

for m in ALL_MODELS:
    admin.add_view(SPECIAL_MAPPING.get(m, AdminModelView)(m))
