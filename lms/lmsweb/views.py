from typing import Any, Callable, Optional

import arrow  # type: ignore
from flask import (
    Response, jsonify, make_response, render_template, request,
    send_from_directory, session, url_for,
)
from flask_babel import gettext as _  # type: ignore
from flask_limiter.util import get_remote_address  # type: ignore
from flask_login import (  # type: ignore
    current_user, login_required, login_user, logout_user,
)
from itsdangerous import BadSignature, SignatureExpired
from werkzeug.datastructures import FileStorage
from werkzeug.utils import redirect

from lms.lmsdb.models import (
    ALL_MODELS, Comment, Course, Note, Role, RoleOptions, SharedSolution,
    Solution, SolutionFile, User, UserCourse, database,
)
from lms.lmsweb import babel, http_basic_auth, limiter, routes, webapp
from lms.lmsweb.admin import (
    AdminModelView, SPECIAL_MAPPING, admin, managers_only,
)
from lms.lmsweb.config import (
    CONFIRMATION_TIME, LANGUAGES, LIMITS_PER_HOUR,
    LIMITS_PER_MINUTE, LOCALE, MAX_UPLOAD_SIZE, REPOSITORY_FOLDER,
)
from lms.lmsweb.forms.change_password import ChangePasswordForm
from lms.lmsweb.forms.register import RegisterForm
from lms.lmsweb.forms.reset_password import RecoverPassForm, ResetPassForm
from lms.lmsweb.git_service import GitService
from lms.lmsweb.manifest import MANIFEST
from lms.lmsweb.redirections import (
    PERMISSIVE_CORS, get_next_url, login_manager,
)
from lms.models import (
    comments, notes, notifications, share_link, solutions, upload,
)
from lms.models.errors import (
    FileSizeError, ForbiddenPermission, LmsError,
    UnauthorizedError, UploadError, fail,
)
from lms.models.users import SERIALIZER, auth, retrieve_salt
from lms.utils.consts import RTL_LANGUAGES
from lms.utils.files import (
    get_language_name_by_extension, get_mime_type_by_extention,
)
from lms.utils.log import log
from lms.utils.mail import (
    send_change_password_mail, send_confirmation_mail,
    send_reset_password_mail,
)

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
def load_user(uuid):
    return User.get_or_none(uuid=uuid)


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
def login(login_message: Optional[str] = None):
    if current_user.is_authenticated:
        return get_next_url(request.args.get('next'))

    username = request.form.get('username')
    password = request.form.get('password')
    next_page = request.form.get('next')
    login_message = request.args.get('login_message')

    if request.method == 'POST':
        try:
            user = auth(username, password)
        except (ForbiddenPermission, UnauthorizedError) as e:
            error_message, _ = e.args
            error_details = {'next': next_page, 'login_message': error_message}
            return redirect(url_for('login', **error_details))
        else:
            login_user(user)
            session['_invalid_password_tries'] = 0
            return get_next_url(next_page)

    return render_template('login.html', login_message=login_message)


@webapp.route('/signup', methods=['GET', 'POST'])
@limiter.limit(f'{LIMITS_PER_MINUTE}/minute;{LIMITS_PER_HOUR}/hour')
def signup():
    if not webapp.config.get('REGISTRATION_OPEN', False):
        return redirect(url_for(
            'login', login_message=_('Can not register now'),
        ))

    form = RegisterForm()
    if not form.validate_on_submit():
        return render_template('signup.html', form=form)

    user = User.create(**{
        User.mail_address.name: form.email.data,
        User.username.name: form.username.data,
        User.fullname.name: form.fullname.data,
        User.role.name: Role.get_unverified_role(),
        User.password.name: form.password.data,
        User.api_key.name: User.random_password(),
    })
    send_confirmation_mail(user)
    return redirect(url_for(
        'login', login_message=_('Registration successfully'),
    ))


@webapp.route('/confirm-email/<int:user_id>/<token>')
@limiter.limit(f'{LIMITS_PER_MINUTE}/minute;{LIMITS_PER_HOUR}/hour')
def confirm_email(user_id: int, token: str):
    user = User.get_or_none(User.id == user_id)
    if user is None:
        return fail(404, 'The authentication code is invalid.')

    if not user.role.is_unverified:
        return fail(403, 'User has been already confirmed.')

    try:
        SERIALIZER.loads(
            token, salt=retrieve_salt(user), max_age=CONFIRMATION_TIME,
        )

    except SignatureExpired:
        send_confirmation_mail(user)
        return redirect(url_for(
            'login', login_message=(
                _(
                    'The confirmation link is expired, new link has been '
                    'sent to your email',
                ),
            ),
        ))
    except BadSignature:
        return fail(404, 'The authentication code is invalid.')

    else:
        update = User.update(
            role=Role.get_student_role(),
        ).where(User.username == user.username)
        update.execute()
        return redirect(url_for(
            'login', login_message=(
                _(
                    'Your user has been successfully confirmed, '
                    'you can now login',
                ),
            ),
        ))


@webapp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    user = User.get(User.id == current_user.id)

    form = ChangePasswordForm(user)
    if not form.validate_on_submit():
        return render_template('change-password.html', form=form)

    user.password = form.password.data
    user.save()
    logout_user()
    send_change_password_mail(user)
    return redirect(url_for(
        'login', login_message=(
            _('Your password has successfully changed'),
        ),
    ))


@webapp.route('/reset-password', methods=['GET', 'POST'])
@limiter.limit(f'{LIMITS_PER_MINUTE}/minute;{LIMITS_PER_HOUR}/hour')
def reset_password():
    form = ResetPassForm()
    if not form.validate_on_submit():
        return render_template('reset-password.html', form=form)

    user = User.get(User.mail_address == form.email.data)

    send_reset_password_mail(user)
    return redirect(url_for(
        'login', login_message=_('Password reset link has successfully sent'),
    ))


@webapp.route(
    '/recover-password/<int:user_id>/<token>', methods=['GET', 'POST'],
)
@limiter.limit(f'{LIMITS_PER_MINUTE}/minute;{LIMITS_PER_HOUR}/hour')
def recover_password(user_id: int, token: str):
    user = User.get_or_none(User.id == user_id)
    if user is None:
        return fail(404, 'The authentication code is invalid.')

    try:
        SERIALIZER.loads(
            token, salt=retrieve_salt(user), max_age=CONFIRMATION_TIME,
        )

    except SignatureExpired:
        return redirect(url_for(
            'login', login_message=(
                _('Reset password link is expired'),
            ),
        ))
    except BadSignature:
        return fail(404, 'The authentication code is invalid.')

    else:
        return recover_password_check(user, token)


def recover_password_check(user: User, token: str):
    form = RecoverPassForm()
    if not form.validate_on_submit():
        return render_template(
            'recover-password.html', form=form, id=user.id, token=token,
        )
    user.password = form.password.data
    user.save()
    return redirect(url_for(
        'login', login_message=(
            _('Your password has successfully changed'),
        ),
    ))


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
    if current_user.is_authenticated and current_user.role.is_banned:
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


@webapp.route('/course/<int:course_id>')
@login_required
def change_last_course_viewed(course_id: int):
    course = Course.get_or_none(course_id)
    if course is None:
        return fail(404, f'No such course {course_id}.')
    user = User.get(User.id == current_user.id)
    if not UserCourse.is_user_registered(user.id, course.id):
        return fail(403, "You're not allowed to access this page.")
    user.last_course_viewed = course
    user.save()
    return redirect(url_for('exercises_page'))


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


@webapp.route('/notes/<int:user_id>', methods=['GET', 'POST'])
@login_required
def note(user_id: int):
    act = request.args.get('act') or request.json.get('act')

    user = User.get_or_none(User.id == user_id)
    if user is None:
        return fail(404, f'No such user {user_id}.')

    if act == 'fetch':
        return jsonify(tuple(user.notes().dicts()))

    if not current_user.role.is_manager:
        return fail(403, "You aren't allowed to access this page.")

    if act == 'delete':
        note_id = int(request.args.get('noteId'))
        return try_or_fail(notes.delete, note_id=note_id)

    if act == 'create':
        note_text = request.args.get('note', '')
        note_exercise = request.args.get('exercise', '')
        privacy = request.args.get('privacy', '0')
        return try_or_fail(
            notes.create,
            user=user,
            note_text=note_text,
            note_exercise=note_exercise,
            privacy=privacy,
        )

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


@webapp.route('/send/<int:course_id>/<int:_exercise_number>')
@login_required
def send(course_id: int, _exercise_number: Optional[int]):
    if not UserCourse.is_user_registered(current_user.id, course_id):
        return fail(403, "You aren't allowed to watch this page.")
    return render_template('upload.html', course_id=course_id)


@webapp.route('/user/<int:user_id>')
@login_required
def user(user_id):
    if user_id != current_user.id and not current_user.role.is_manager:
        return fail(403, "You aren't allowed to watch this page.")
    target_user = User.get_or_none(User.id == user_id)
    if target_user is None:
        return fail(404, 'There is no such user.')

    is_manager = current_user.role.is_manager

    return render_template(
        'user.html',
        solutions=Solution.of_user(
            target_user.id, with_archived=True, from_all_courses=True,
        ),
        user=target_user,
        is_manager=is_manager,
        notes_options=Note.get_note_options(),
    )


@webapp.route('/send/<int:course_id>', methods=['GET'])
@login_required
def send_(course_id: int):
    if not UserCourse.is_user_registered(current_user.id, course_id):
        return fail(403, "You aren't allowed to watch this page.")
    return render_template('upload.html', course_id=course_id)


@webapp.route('/upload/<int:course_id>', methods=['POST'])
@login_required
def upload_page(course_id: int):
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
        matches, misses = upload.new(user.id, course_id, file)
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
        filename=f'{filename}.zip'.encode('utf-8'),
    )
    return response


@webapp.route(f'{routes.GIT}/info/refs')
@webapp.route(f'{routes.GIT}/git-receive-pack', methods=['POST'])
@webapp.route(f'{routes.GIT}/git-upload-pack', methods=['POST'])
@http_basic_auth.login_required
def git_handler(course_id: int, exercise_number: int) -> Response:
    git_service = GitService(
        user=http_basic_auth.current_user(),
        exercise_number=exercise_number,
        course_id=course_id,
        request=request,
        base_repository_folder=REPOSITORY_FOLDER,
    )
    return git_service.handle_operation()


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

    if viewer_is_solver:
        solution.view_solution()

    return render_template('view.html', **view_params)


@webapp.route(f'{routes.SHARED}/<string:shared_url>')
@webapp.route(f'{routes.SHARED}/<string:shared_url>/<int:file_id>')
@login_required
@limiter.limit(f'{LIMITS_PER_MINUTE}/minute')
def shared_solution(shared_url: str, file_id: Optional[int] = None):
    if not webapp.config.get('SHAREABLE_SOLUTIONS', False):
        return fail(404, 'Solutions are not shareable.')

    shared_solution = SharedSolution.get_or_none(
        SharedSolution.shared_url == shared_url,
    )
    if shared_solution is None:
        return fail(404, 'The solution does not exist.')

    share_link.new(shared_solution)
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
    return {'direction': DIRECTION}


@webapp.template_filter('mime_type')
def _jinja2_filter_path_to_mime_type(filename: str) -> str:
    ext = '.' + filename.path.rsplit('.')[-1]
    return get_mime_type_by_extention(ext)


DIRECTION = 'rtl' if get_locale() in RTL_LANGUAGES else 'ltr'


for m in ALL_MODELS:
    admin.add_view(SPECIAL_MAPPING.get(m, AdminModelView)(m))
