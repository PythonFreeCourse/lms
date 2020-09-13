import os
from functools import wraps
from typing import Optional
from urllib.parse import urljoin, urlparse

import arrow  # type: ignore
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
    ALL_MODELS, Comment, CommentText, Exercise, RoleOptions,
    Solution, SolutionFile, User, database,
)
from lms.lmsweb import routes, webapp
from lms.models import notifications, solutions, upload
from lms.models.errors import AlreadyExists, BadUploadFile
from lms.utils.log import log

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
MAX_REQUEST_SIZE = 2_000_000  # 2MB (in bytes)


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


@webapp.before_request
def banned_page():
    if (
        current_user.is_authenticated
        and current_user.role.is_banned
    ):
        return render_template('banned.html')


@webapp.route('/')
@login_required
def main():
    return redirect(url_for('exercises_page'))


@webapp.route(routes.STATUS)
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
    file: SolutionFile,
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
        file=file,
    )

    return jsonify({
        'success': 'true', 'text': comment_.comment.text,
        'author_name': user.fullname, 'is_auto': False, 'id': comment_.id,
        'line_number': line_number,
    })


@webapp.route('/notifications')
@login_required
def get_notifications():
    response = notifications.get(user=current_user)
    return jsonify(response)


@webapp.route('/read', methods=['PATCH'])
def read_all_notification():
    success_state = notifications.read(user=current_user)
    return jsonify({'success': success_state})


@webapp.route('/comments', methods=['GET', 'POST'])
@login_required
def comment():
    act = request.args.get('act') or request.json.get('act')

    if request.method == 'POST':
        file_id = int(request.json.get('fileId', 0))
    else:  # it's a GET
        file_id = int(request.args.get('fileId', 0))

    file = SolutionFile.get_or_none(file_id)
    if file is None:
        return fail(404, f'No such file {file_id}')

    solver_id = file.solution.solver.id
    if solver_id != current_user.id and not current_user.role.is_manager:
        return fail(403, "You aren't allowed to access this page.")

    if act == 'fetch':
        return jsonify(Comment.by_file(file_id))

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
            file,
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


@webapp.route('/user/<int:user_id>')
@login_required
def user(user_id):
    if user_id != current_user.id and not current_user.role.is_manager:
        return fail(403, "You aren't allowed to watch this page.")
    target_user = User.get_or_none(User.id == user_id)
    if target_user is None:
        return fail(404, 'There is no such user.')

    return render_template(
        'user.html',
        solutions=Solution.of_user(target_user.id, with_archived=True),
        user=target_user,
    )


@webapp.route('/send', methods=['GET'])
@login_required
def send_():
    return render_template('upload.html')


@webapp.route('/upload', methods=['POST'])
@login_required
def upload_page():
    user_id = current_user.id
    user = User.get_or_none(User.id == user_id)  # should never happen
    if user is None:
        return fail(404, 'User not found')
    if request.content_length > MAX_REQUEST_SIZE:
        return fail(
            413, f'File is too big. {MAX_REQUEST_SIZE // 1000000}MB allowed',
        )

    file: Optional[FileStorage] = request.files.get('file')
    if file is None:
        return fail(422, 'No file was given')

    try:
        matches, misses = upload.new(user, file)
    except (AlreadyExists, BadUploadFile) as e:
        log.debug(e)
        return fail(400, str(e))

    return jsonify({
        'exercise_matches': matches,
        'exercise_misses': misses,
    })


@webapp.route(f'{routes.SOLUTIONS}/<int:solution_id>')
@webapp.route(f'{routes.SOLUTIONS}/<int:solution_id>/<int:file_id>')
@login_required
def view(solution_id: int, file_id: Optional[int] = None):
    solution = Solution.get_or_none(Solution.id == solution_id)
    if solution is None:
        return fail(404, 'Solution does not exist.')

    viewer_is_solver = solution.solver.id == current_user.id
    has_viewer_access = current_user.role.is_viewer
    if not viewer_is_solver and not has_viewer_access:
        return fail(403, 'This user has no permissions to view this page.')

    versions = solution.ordered_versions()
    test_results = solution.test_results()
    is_manager = current_user.role.is_manager

    solution_files = tuple(solution.files)
    if not solution_files:
        if not is_manager:
            return fail(404, 'There are no files in this solution.')
        return done_checking(solution.exercise.id, solution.id)

    files = solutions.get_files_tree(solution.files)
    file_id = file_id or files[0]['id']
    file_to_show = next((f for f in solution_files if f.id == file_id), None)
    if file_to_show is None:
        return fail(404, 'File does not exist.')

    view_params = {
        'solution': model_to_dict(solution),
        'files': files,
        'comments': solution.comments_per_file,
        'current_file': file_to_show,
        'is_manager': is_manager,
        'role': current_user.role.name.lower(),
        'versions': versions,
        'test_results': test_results,
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
            'left': Solution.left_in_exercise(solution.exercise),
        }

    if viewer_is_solver:
        notifications.read_related(solution_id, current_user.id)

    return render_template('view.html', **view_params)


@webapp.route('/checked/<int:exercise_id>/<int:solution_id>', methods=['POST'])
@login_required
@managers_only
def done_checking(exercise_id, solution_id):
    is_updated = solutions.mark_as_checked(solution_id, current_user.id)
    next_solution = solutions.get_next_unchecked(exercise_id)
    next_solution_id = getattr(next_solution, 'id', None)
    return jsonify({'success': is_updated, 'next': next_solution_id})


@webapp.route('/check/<int:exercise_id>')
@login_required
@managers_only
def start_checking(exercise_id):
    next_solution = solutions.get_next_unchecked(exercise_id)
    if solutions.start_checking(next_solution):
        return redirect(f'{routes.SOLUTIONS}/{next_solution.id}')
    return redirect(routes.STATUS)


def _common_comments(exercise_id=None, user_id=None):
    """
    Most common comments throughout all exercises.
    Filter by exercise id when specified.
    """
    query = CommentText.filter(**{
        CommentText.flake8_key.name: None,
    }).select(CommentText.id, CommentText.text).join(Comment)

    if exercise_id is not None:
        query = (
            query
            .join(SolutionFile)
            .join(Solution)
            .join(Exercise)
            .where(Exercise.id == exercise_id)
        )

    if user_id is not None:
        query = (
            query
            .filter(Comment.commenter == user_id)
        )

    query = (
        query
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


@webapp.template_filter('date_humanize')
def _jinja2_filter_datetime(date):
    try:
        return arrow.get(date).humanize(locale='he_IL')
    except ValueError:
        return str(arrow.get(date).date())


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
