from functools import wraps

from flask_admin import Admin, AdminIndexView  # type: ignore
from flask_admin.contrib.peewee import ModelView  # type: ignore
from flask_login import current_user

from lms.lmsdb.models import Comment, CommentText, Solution
from lms.lmsweb import webapp
from lms.models.errors import fail


def managers_only(func):
    # Must have @wraps to work with endpoints.
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.role.is_manager:
            return fail(403, 'This user has no permissions to view this page.')
        else:
            return func(*args, **kwargs)

    return wrapper


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
    index_view=MyAdminIndexView(),  # NOQA
)
