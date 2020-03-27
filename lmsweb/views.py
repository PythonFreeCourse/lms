import json
from datetime import datetime
from functools import wraps
from typing import Optional
from urllib.parse import urljoin, urlparse

from flask import (
    abort, jsonify, render_template, request, url_for,
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


def managers_only(func):
    """Decorator enforrcing access for managers only"""

    # Must have @wraps to work with endpoints.
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.role.is_manager:
            return fail(403, "This user has no permissions to view this page.")
        else:
            return func(*args, **kwargs)

    return wrapper


def fail(status_code: int, error_msg: str):
    data = {
        'status': 'failed',
        'msg': error_msg
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


@webapp.route('/')
@login_required
def main():
    return redirect(url_for('exercises_page'))


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
    exercises = fetch_exercises()
    solutions = fetch_solutions(current_user.id)
    is_manager = current_user.role.is_manager
    return render_template(
        'exercises.html',
        exercises=exercises, solutions=solutions, is_manager=is_manager,
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
        return fail(400, "Invalid kind")

    if line_number <= 0:
        return fail(422, f"Invalid line number: {line_number}")

    if kind == 'id':
        new_comment_id = comment_id
    elif kind == 'text':
        if not comment_text:
            return fail(422, 'Empty comments are not allowed')
            # TODO(LOW): Check if line number > MAX_SOLUTION_LINE_NUMBER
        new_comment_id = CommentText.get_or_create(text=comment_text)[0].id
    else:
        # should never happend, kind was checked before
        return fail(400, "Invalid kind")

    comment_ = Comment.create(
        commenter=user,
        line_number=line_number,
        comment=new_comment_id,
        solution=solution
    )

    return jsonify({
        'success': 'true', 'id': comment_.id, 'text': comment_.comment.text,
    })


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
        return fail(404, f"No such solution {solution_id}")

    solver_id = solution.solver.id
    if solver_id != current_user.id and current_user.role.is_manager:
        return fail(401, "You aren't allowed to watch this page.")

    if act == 'fetch':
        return jsonify(Comment.by_solution(solution_id))

    if act == 'delete':
        comment_id = int(request.args.get('commentId'))
        comment_ = Comment.get_or_none(Comment.id == comment_id)
        if comment_ is not None:
            comment_.delete_instance()
        return jsonify({"success": "true"})

    if act == 'create':
        kind = request.json.get('kind', '')
        comment_id, comment_text = None, None
        try:
            line_number = int(request.json.get('line', 0))
        except ValueError:
            line_number = 0
        if kind.lower() == 'id':
            comment_id = int(request.json.get("comment", 0))
        if kind.lower() == 'text':
            comment_text = request.json.get("comment", '')
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


@webapp.route('/upload', methods=['POST'])
@login_required
def upload():
    user_id = request.form.get('user')
    if user_id is None or user_id != current_user.id:
        return fail(403, "Wrong user ID.")

    exercise = Exercise.get_by_id(request.form.get('exercise'))
    if not exercise:
        return fail(404, "Exercise does not exist.")

    user = User.get_by_id(user_id)
    if not user:
        return fail(403, "Invalid user.")

    if request.content_length > MAX_REQUEST_SIZE:
        return fail(413, "File is too heavy. 500KB allowed")

    file: FileStorage = request.files.get('file')
    if not file:
        return fail(402, "No file was given")

    json_file_data = file.read()
    try:
        file_content = json.loads(json_file_data)
        exercises = list(extract_exercises(file_content))
    except (ValueError, json.JSONDecodeError):
        return fail(422, "Invalid file format - must be ipynb")

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

    return jsonify({
        "exercise_matches": list(valid),
        "exercise_misses": list(misses),
        "exercise_duplications": list(duplications)
    })


@webapp.route('/view/<int:solution_id>')
@login_required
def view(solution_id):
    solution = Solution.get_or_none(Solution.id == solution_id)
    if solution is None:
        return fail(404, "Solution does not exist.")

    is_manager = current_user.role.is_manager
    if solution.solver.id != current_user.id and not is_manager:
        return fail(403, "This user has no permissions to view this page.")

    view_params = {
        'solution': model_to_dict(solution),
        'is_manager': is_manager,
        'role': current_user.role.name.lower(),
    }

    if is_manager:
        view_params = {
            **view_params,
            'exercise_common_comments': _common_comments(solution.exercise),
            'all_common_comments': _common_comments(),
        }

    return render_template('view.html', **view_params)


@webapp.route('/checked/<int:exercise_id>/<int:solution_id>', methods=['POST'])
@login_required
@managers_only
def done_checking(exercise_id, solution_id):
    requested_solution = (Solution.id == solution_id)
    changes = Solution.update(
        is_checked=True, checker=current_user.id,
    ).where(requested_solution)
    is_updated = changes.execute() == 1
    next_exercise = Solution.next_unchecked_of(exercise_id).get('id')
    return jsonify({'success': is_updated, 'next': next_exercise})


@webapp.route('/check/<int:exercise_id>')
@login_required
@managers_only
def start_checking(exercise_id):
    if exercise_id != 0:
        next_exercise = Solution.next_unchecked_of(exercise_id).get('id')
    else:
        next_exercise = Solution.next_unchecked().get('id')
    if next_exercise is not None:
        return redirect(f'/view/{next_exercise}')
    return redirect('/exercises')


def _common_comments(exercise_id=None):
    """
    Most common comments throughout all exercises.
    Filter by exercise id when specified.
    """
    query = CommentText.select(CommentText.id, CommentText.text)
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
@managers_only
def common_comments(exercise_id=None):
    return jsonify(_common_comments(exercise_id=exercise_id))
