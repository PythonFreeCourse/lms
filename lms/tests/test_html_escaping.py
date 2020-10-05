from flask import json

from lms.lmsdb.models import Solution, User
from lms.tests import conftest


USER_COMMENT_BEFORE_ESCAPING = '<html><body><p>Welcome "LMS"</p></body></html>'
USER_COMMENT_AFTER_ESCAPING = (
    '&lt;html&gt;&lt;body&gt;&lt;p&gt;Welcome &quot;LMS&quot;'
    '&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;'
)


class TestHtmlEscaping:
    @staticmethod
    def test_comment_text_escaping(student_user: User, solution: Solution):
        client = conftest.get_logged_user(student_user.username)

        # Creating a comment
        comment_response = client.post('/comments', data=json.dumps(dict(
            fileId=solution.files[0].id, act='create', kind='text',
            comment=USER_COMMENT_BEFORE_ESCAPING, line=1,
        )), content_type='application/json')
        assert comment_response.status_code == 200
        assert solution.comments[0].comment.text == USER_COMMENT_AFTER_ESCAPING
