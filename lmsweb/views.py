import json
from datetime import datetime
from urllib.parse import urljoin, urlparse


from flask import (
    abort, jsonify, render_template, request, session, url_for,
)
from flask_login import (  # type: ignore
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from peewee import fn  # type: ignore
from playhouse.shortcuts import model_to_dict  # type: ignore
from werkzeug.datastructures import FileStorage
from werkzeug.utils import redirect

from lms.lmsweb import webapp
from lms.lmsweb.models import (
    Comment, CommentText, Exercise, RoleOptions, Solution, User, database,
)
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


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return (
        test_url.scheme in ('http', 'https')
        and ref_url.netloc == test_url.netloc
    )


def redirect_logged_in(func):
    """Must wrap the route"""

    def wrapper(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect(url_for('main'))
        else:
            return func(*args, **kwargs)

    return wrapper


@redirect_logged_in
@webapp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('id') is not None and session.get('invalid') is not True:
        return redirect(url_for('main'))

    username = request.form.get('username')
    password = request.form.get('password')
    user = User.get_or_none(username=username)

    if user is not None and user.is_password_valid(password):
        session['invalid'] = False
        login_user(user)
        for field in ('username', 'role', 'id'):
            session[field] = str(getattr(user, field))
        next_url = request.args.get('next_url')
        if not is_safe_url(next_url):
            return abort(400)
        return redirect(next_url or url_for('main'))

    return render_template('login.html')


@webapp.route('/logout')
@login_required
def logout():
    session['invalid'] = True
    logout_user()
    return redirect('login')


@webapp.route('/')
@login_required
def main():
    if session.get('id') is not None:
        return redirect(url_for('exercises_page'))
    return redirect(url_for('login'))


def fetch_exercises():
    not_archived_filter = {Exercise.is_archived.name: False}
    unarchived_exercises = Exercise.filter(**not_archived_filter)
    return tuple(unarchived_exercises.dicts())


def fetch_solutions(user_id):
    fields = [
        Solution.id, Solution.is_checked, Solution.grade,
        Solution.submission_timestamp, Solution.exercise,
    ]
    solutions = Solution.select(*fields).where(Solution.solver == user_id)
    return {d['id']: d for d in solutions.dicts()}


@webapp.route('/exercises')
@login_required
def exercises_page():
    user_id = int(session['id'])
    exercises = fetch_exercises()
    solutions = fetch_solutions(user_id)
    return render_template(
        'exercises.html', exercises=exercises, solutions=solutions,
    )


@webapp.route('/comments', methods=['GET', 'POST'])
@login_required
def comment():
    is_manager = session['role'] in HIGH_ROLES
    if is_manager and request.method == 'POST':
        solutionId = request.form['solutionId']
        print(solutionId)
        return jsonify('{"success": "true"}')

    if request.method != 'GET':
        return abort(405, "Must be GET or POST")

    solution_id = int(request.args['solutionId'])
    solution = Solution.get(solution_id)
    if is_manager or solution.solver.id == int(session['id']):
        if request.args.get('act') == 'fetch':
            return jsonify(Comment.by_solution(solution_id))
        if not is_manager:
            abort(403, "Permission denied")
        if request.args.get('act') == 'delete':
            comment_id = int(request.args.get('commentId'))
            # TODO: Handle if not found
            Comment.get(
                Comment.comment == comment_id,
                Comment.solution == solution_id,
            ).delete_instance()
            return jsonify({"success": "true"})


@webapp.route('/send/<int:_exercise_id>')
@login_required
def send(_exercise_id):
    return render_template('upload.html')


@webapp.route('/upload', methods=['POST'])
@login_required
def upload():
    user_id = request.form.get('user')
    if user_id is None or int(session['id']) != user_id:
        return abort(403, "Wrong user ID.")

    exercise = Exercise.get_by_id(request.form.get('exercise'))
    if not exercise:
        return abort(404, "Exercise does not exist.")

    user = User.get_by_id(user_id)
    if not user:
        return abort(403, "Invalid user.")

    if request.content_length > MAX_REQUEST_SIZE:
        return abort(402, "file is too heavy. 500KB allowed")

    file: FileStorage = request.files.get('file')
    if not file:
        return abort(402, "no file was given")

    json_file_data = file.read()
    try:
        file_content = json.loads(json_file_data)
        exercises = list(extract_exercises(file_content))
    except (ValueError, json.JSONDecodeError):
        return abort(422, "Invalid file format - must be ipynb")

    matches, misses, duplications = set(), set(), set()
    for exercise_id, code in exercises:
        exercise = Exercise.get_or_none(Exercise.subject == exercise_id)
        if exercise is None:
            misses.add(exercise_id)
            continue
        solution, created = Solution.get_or_create(
            exercise=exercise,
            solver=user,
            defaults={
                'submission_timestamp': datetime.now(),
                'json_data_str': code,
            }
        )
        if created:
            matches.add(exercise_id)
        else:
            solution.delete_instance()
            duplications.add(exercise_id)

    valid = matches - duplications

    return json.dumps({
            "exercise_matches": list(valid),
            "exercise_misses": list(misses),
            "exercise_duplications": list(duplications)
    })


@webapp.route('/view/<int:solution_id>')
@login_required
def view(solution_id):
    solution = Solution.get_or_none(Solution.id == solution_id)
    is_manager = session['role'] in HIGH_ROLES
    if solution is None:
        return abort(404, "Solution does not exist.")
    if solution.solver.id != int(session['id']) and not is_manager:
        return abort(403, "This user has no permissions to view this page.")

    view_params = {
        'solution': model_to_dict(solution), 'is_manager': is_manager,
        'role': session['role'].lower(),
    }

    if is_manager:
        view_params = {
            **view_params,
            'exercise_common_comments': common_comments(solution.exercise),
            'all_common_comments': common_comments(solution.exercise),
        }

    return render_template('view.html', **view_params)


@webapp.route('/checked/<int:solution_id>', methods=['POST'])
@login_required
def done_checking(solution_id):
    if session['role'] not in HIGH_ROLES:
        return abort(403, "This user has no permissions to view this page.")

    requested_solution = Solution.id == solution_id
    changes = Solution.update(
        is_checked=True, checker=int(session['id']),
    ).where(requested_solution)
    next_exercise = 1  # TODO: Change to get_next_unchecked()
    return jsonify({'success': changes.execute() == 1, 'next': next_exercise})


def common_comments(exercise_id=None):
    # TODO: Add cache for 2 minute each time
    """
    Most common comments throughout all exercises.
    Filter by exercise id when specified.
    """
    if session['role'] not in HIGH_ROLES:
        return abort(403, "This user has no permissions to view this page.")

    query = CommentText.select(CommentText.text)
    if exercise_id is not None:
        query = (query
                 .join(Comment)
                 .join(Solution)
                 .join(Exercise)
                 .where(Exercise.id == exercise_id)
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
def _common_comments(exercise_id=None):
    return jsonify(common_comments(exercise_id=None))
