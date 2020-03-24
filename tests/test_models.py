from lmsweb.models import User, Exercise, CommentText
from tests.conftest import SUBJECT, COMMENT_TEXT


class TestExercise:
    def test_exercise(self, user: User, exercise: Exercise, comment: CommentText):
        e = Exercise.get(Exercise.subject == SUBJECT)
        c = CommentText.get(CommentText.commenter == user)
        assert e and c
        assert c.exercise == e
        assert c.comment_text == COMMENT_TEXT
        assert c.line_number == 1
