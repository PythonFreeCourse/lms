import os
import shutil
import tempfile

from lms import lmsnotifications
from lms.lmsdb import models
from lms.lmstests.public.flake8 import tasks

INVALID_CODE = 'print "Hello Word" '
INVALID_CODE_MESSAGE = 'כשהבודק שלנו ניסה להריץ את הקוד שלך, הוא ראה שלפייתון יש בעיה להבין אותו. כדאי לוודא שהקוד רץ כהלכה לפני שמגישים אותו.'  # noqa E501
INVALID_CODE_KEY = 'E999'
VALID_CODE = 'print(0)'

EXECUTE_CODE = ('import os\n'
                'eval(\'os.system("touch {}")\')')


class TestAutoFlake8:
    test_directory = None

    @classmethod
    def setup_class(cls):
        cls.test_directory = tempfile.mkdtemp()
        cls.file_path = os.path.join(cls.test_directory, 'some-file')
        cls.execute_script = EXECUTE_CODE.format(cls.file_path)

    @classmethod
    def teardown_class(cls):
        if cls.test_directory is not None:
            shutil.rmtree(cls.test_directory)

    def test_pyflake_wont_execute_code(self, solution: models.Solution):
        solution.json_data_str = self.execute_script
        solution.save()
        tasks.run_flake8_on_solution(solution.id)
        comments = tuple(
            models.Comment.filter(models.Comment.solution == solution))
        assert not os.listdir(self.test_directory)
        assert len(comments) == 2
        exec(compile(self.execute_script, '', 'exec'))  # noqa S102
        assert os.listdir(self.test_directory) == ['some-file']

    def test_invalid_solution(self, solution: models.Solution):
        solution.json_data_str = INVALID_CODE
        solution.save()
        tasks.run_flake8_on_solution(solution.id)
        comments = tuple(
            models.Comment.filter(models.Comment.solution == solution))
        assert comments
        assert len(comments) == 1
        comment = comments[0].comment
        assert comment.text == INVALID_CODE_MESSAGE
        assert comment.flake8_key == INVALID_CODE_KEY
        messages = lmsnotifications.get_messages_for_user(for_user=solution.solver)
        assert len(messages) == 1
        expected = f'נמצאו 1 תקלות בבדיקה האוטומטית עבור התרגיל {solution.exercise.subject}'
        assert expected == messages[0][models.Notification.MESSAGE_FIELD_NAME]

    def test_valid_solution(self, solution: models.Solution):
        solution.json_data_str = VALID_CODE
        solution.save()
        tasks.run_flake8_on_solution(solution.id)
        comments = tuple(
            models.Comment.filter(models.Comment.solution == solution))
        assert not comments
