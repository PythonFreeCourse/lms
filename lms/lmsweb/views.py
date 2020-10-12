from typing import Any, Callable, Optional

import arrow  # type: ignore
from flask import (
    jsonify, make_response, render_template,
    request, send_from_directory, url_for,
)
from flask_limiter.util import get_remote_address  # type: ignore
from flask_login import (  # type: ignore
    current_user, login_required, login_user, logout_user,
)
from werkzeug.datastructures import FileStorage
from werkzeug.utils import redirect

from lms.lmsdb.models import (
    ALL_MODELS, Comment, RoleOptions, SharedSolution,
    Solution, SolutionFile, User, database,
)
from lms.lmsweb import babel, limiter, routes, webapp
from lms.lmsweb.admin import (
    AdminModelView, SPECIAL_MAPPING, admin, managers_only,
)
from lms.lmsweb.config import (
    LANGUAGES, LIMITS_PER_HOUR, LIMITS_PER_MINUTE, LOCALE, MAX_UPLOAD_SIZE,
)
from lms.lmsweb.manifest import MANIFEST
from lms.lmsweb.redirections import (
    PERMISSIVE_CORS, get_next_url, login_manager,
)
from lms.models import comments, notifications, share_link, solutions, upload
from lms.models.errors import FileSizeError, LmsError, UploadError, fail
from lms.utils.consts import RTL_LANGUAGES
from lms.utils.files import get_language_name_by_extension
from lms.utils.log import log


HIGH_ROLES = {str(RoleOptions.STAFF), str(RoleOptions.ADMINISTRATOR)}


@babel.localeselector
def get_locale():
    if LOCALE in LANGUAGES:
        return LOCALE
    return 'en'


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


@webapp.errorhandler(429)
def ratelimit_handler(e):
    log.info(f'IP Address: {get_remote_address()}: {e}')
    return make_response(
        jsonify(error='ratelimit exceeded %s' % e.description), 429,
    )


@webapp.route('/login', methods=['GET', 'POST'])
@limiter.limit(
    f'{LIMITS_PER_MINUTE}/minute;{LIMITS_PER_HOUR}/hour',
    deduct_when=lambda response: response.status_code != 200,
)
def login():
    if current_user.is_authenticated:
        return get_next_url(request.args.get('next'))

    username = request.form.get('username')
    password = request.form.get('password')
    next_page = request.form.get('next')
    user = User.get_or_none(username=username)

    if user is not None and user.is_password_valid(password):
        login_user(user)
        return get_next_url(next_page)
    elif user is not None:
        return redirect(url_for('login', **{'next': next_page}))

    return render_template('login.html')


@webapp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('login')


@webapp.route('/favicon.ico')
def favicon():
    return send_from_directory(
        webapp.static_folder,
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon',
    )


@webapp.route('/manifest.json')
def manifest():
    return jsonify(MANIFEST)


@webapp.route('/sw.js')
def service_worker():
    response = make_response(
        send_from_directory(webapp.static_folder, 'sw.js'),
    )
    response.headers['Cache-Control'] = 'no-cache'
    return response


@webapp.before_request
def banned_page():
    if (
        current_user.is_authenticated
        and current_user.role.is_banned
    ):
        return render_template('banned.html')


def try_or_fail(callback: Callable, *args: Any, **kwargs: Any):
    try:
        result = callback(*args, **kwargs)
    except LmsError as e:
        error_message, status_code = e.args
        return fail(status_code, error_message)
    return result or jsonify({'success': 'true'})


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


@webapp.route('/notifications')
@login_required
def get_notifications():
    response = notifications.get(user=current_user)
    return jsonify(response)


@webapp.route('/read', methods=['PATCH'])
def read_all_notification():
    success_state = notifications.read(user=current_user)
    return jsonify({'success': success_state})


@webapp.route('/share', methods=['POST'])
@login_required
def share():
    act = request.json.get('act')
    solution_id = int(request.json.get('solutionId', 0))

    try:
        shared_solution = share_link.get(solution_id)
    except LmsError as e:
        error_message, status_code = e.args
        return fail(status_code, error_message)

    if act == 'get':
        return jsonify({
            'success': 'true',
            'share_link': shared_solution.shared_url,
        })
    elif act == 'delete':
        shared_solution.delete_instance()
        return jsonify({
            'success': 'true',
            'share_link': 'false',
        })

    return fail(400, f'Unknown or unset act value "{act}".')


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
        return fail(404, f'No such file {file_id}.')

    solver_id = file.solution.solver.id
    if solver_id != current_user.id and not current_user.role.is_manager:
        return fail(403, "You aren't allowed to access this page.")

    if act == 'fetch':
        return jsonify(Comment.by_file(file_id))

    if (
        not webapp.config.get('USERS_COMMENTS', False)
        and not current_user.role.is_manager
    ):
        return fail(403, "You aren't allowed to access this page.")

    if act == 'delete':
        return try_or_fail(comments.delete)

    if act == 'create':
        user = User.get_or_none(User.id == current_user.id)
        try:
            comment_ = comments.create(file=file, user=user)
        except LmsError as e:
            error_message, status_code = e.args
            return fail(status_code, error_message)

        return jsonify({
            'success': 'true', 'text': comment_.comment.text, 'is_auto': False,
            'author_name': user.fullname, 'author_role': user.role.id,
            'id': comment_.id, 'line_number': comment_.line_number,
        })

    return fail(400, f'Unknown or unset act value "{act}".')


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
        return fail(404, 'User not found.')
    if request.content_length > MAX_UPLOAD_SIZE:
        return fail(
            413, f'File is too big. {MAX_UPLOAD_SIZE // 1000000}MB allowed.',
        )

    file: Optional[FileStorage] = request.files.get('file')
    if file is None:
        return fail(422, 'No file was given.')

    try:
        matches, misses = upload.new(user, file)
    except UploadError as e:
        log.debug(e)
        return fail(400, str(e))
    except FileSizeError as e:
        log.debug(e)
        return fail(413, str(e))

    return jsonify({
        'exercise_matches': matches,
        'exercise_misses': misses,
    })


@webapp.route(f'{routes.DOWNLOADS}/<string:download_id>')
@login_required
def download(download_id: str):
    """Downloading a zip file of the code files.

    Args:
        download_id (str): Can be on each side of
                           a solution.id and sharedsolution.shared_url.
    """
    try:
        files, filename = solutions.get_download_data(download_id)
    except LmsError as e:
        error_message, status_code = e.args
        return fail(status_code, error_message)

    response = make_response(solutions.create_zip_from_solution(files))
    response.headers.set('Content-Type', 'zip')
    response.headers.set(
        'Content-Disposition', 'attachment',
        filename=f'{filename}.zip',
    )
    return response


@webapp.route(f'{routes.SOLUTIONS}/<int:solution_id>')
@webapp.route(f'{routes.SOLUTIONS}/<int:solution_id>/<int:file_id>')
@login_required
def view(
    solution_id: int, file_id: Optional[int] = None, shared_url: str = '',
):
    solution = Solution.get_or_none(Solution.id == solution_id)
    if solution is None:
        return fail(404, 'Solution does not exist.')

    viewer_is_solver = solution.solver.id == current_user.id
    has_viewer_access = current_user.role.is_viewer
    if not shared_url and not viewer_is_solver and not has_viewer_access:
        return fail(403, 'This user has no permissions to view this page.')

    is_manager = current_user.role.is_manager

    solution_files = tuple(solution.files)
    if not solution_files:
        if not is_manager:
            return fail(404, 'There are no files in this solution.')
        return done_checking(solution.exercise.id, solution.id)

    try:
        view_params = solutions.get_view_parameters(
            solution, file_id, shared_url, is_manager,
            solution_files, viewer_is_solver,
        )
    except LmsError as e:
        error_message, status_code = e.args
        return fail(status_code, error_message)

    return render_template('view.html', **view_params)


@webapp.route(f'{routes.SHARED}/<string:shared_url>')
@webapp.route(f'{routes.SHARED}/<string:shared_url>/<int:file_id>')
@login_required
def shared_solution(shared_url: str, file_id: Optional[int] = None):
    if not webapp.config.get('SHAREABLE_SOLUTIONS', False):
        return fail(404, 'Solutions are not shareable.')

    shared_solution = SharedSolution.get_or_none(
        SharedSolution.shared_url == shared_url,
    )
    if shared_solution is None:
        return fail(404, 'The solution does not exist.')

    solution_id = shared_solution.solution.id
    return view(
        solution_id=solution_id, file_id=file_id, shared_url=shared_url,
    )


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


@webapp.route('/common_comments')
@webapp.route('/common_comments/<exercise_id>')
@login_required
@managers_only
def common_comments(exercise_id=None):
    return jsonify(comments._common_comments(exercise_id=exercise_id))


@webapp.template_filter('date_humanize')
def _jinja2_filter_datetime(date):
    try:
        return arrow.get(date).humanize(locale=get_locale())
    except ValueError:
        return str(arrow.get(date).date())


@webapp.template_filter('language_name')
def _jinja2_filter_path_to_language_name(filename: str) -> str:
    ext = filename.path.rsplit('.')[-1]
    return get_language_name_by_extension(ext)


@webapp.context_processor
def _jinja2_inject_direction():
    return dict(direction=DIRECTION)


DIRECTION = 'rtl' if get_locale() in RTL_LANGUAGES else 'ltr'


for m in ALL_MODELS:
    admin.add_view(SPECIAL_MAPPING.get(m, AdminModelView)(m))
