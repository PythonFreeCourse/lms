import base64
import os.path
import shutil
import tempfile
from unittest import mock

from flask.testing import FlaskClient

from lms.lmsdb import models
from lms.lmsweb import webapp
from tests import conftest


POST_NEW_REPOSITORY_BUFFER = \
    b'00ab0000000000000000000000000000000000000000 ' \
    b'c1d42352fc88ae88fde7713c23232d7d0703849a refs/heads/master\x00 ' \
    b'report-status-v2 side-band-64k object-format=sha1 ' \
    b'agent=git/2.30.10000PACK\x00\x00\x00\x02\x00\x00\x00\x03\x9d\nx' \
    b'\x9c\x95\xccA\n\xc3 \x10@\xd1\xbd\xa7p_(3\x8e\x9a\x04J\xe8\xae' \
    b'\x07\xe8\t\xa6\x99\xd1\n\x9a\x80\xd8\xfb7\xd0\x13t\xfb\xe1\xfd' \
    b'\xd1U\xed$@\xc2\x92\x92\xdf\xd2\x1c\xf1\x15@\x84=\x12\xba\xa4' \
    b'\xea\xe6e\x89\x88\x12\x12\x1a\xfe\x8c\xf7\xd1\xed\x83\xab}\x96=k' \
    b'\xb7\xb7\xcc\xd5\x93\xbb\xe7\xc6\xa5^\xb7\xa3\xad\x16#\x91\x9b' \
    b'\xc0\x07\xb2\x17 \x00s\xd6V\xc6\xd0\xbf\xa1){)\xe34\xbf\x83\xf9' \
    b'\x02\xa5\x1f3_\xa0\x02x\x9c340031Q(\xc8,Id(M^\xc86;\xe0\xd1\x1d' \
    b'\xefZ\x8bP\x17\x8eU\xd2\x17\xcb\xb6\xc6\x01\x00\xab:\x0b\xe64x' \
    b'\x9c+O\xcc\xe6\x02\x00\x03\xe3\x01NvHX\x85>M\xf7I\xd6\x7fGZ' \
    b'\x0e^\xc8\x82Q\xe3\xcb\xd9'


POST_CLONE_REPOSITORY_BUFFER = \
    b'0098want c1d42352fc88ae88fde7713c23232d7d0703849a multi_ack_detailed' \
    b' no-done side-band-64k thin-pack ofs-delta deepen-since deepen-not' \
    b' agent=git/2.30.1\n00000009done\n'


class TestSendSolutionFromGit:
    INFO_URL = 'info/refs'
    GET_METHOD = FlaskClient.get.__name__
    POST_METHOD = FlaskClient.post.__name__

    temp_folder = ''

    def setup_method(self, _method: str) -> None:
        self.temp_folder = tempfile.mkdtemp()

    def teardown_method(self, _method: str) -> None:
        if self.temp_folder and os.path.exists(self.temp_folder):
            shutil.rmtree(self.temp_folder)

    @staticmethod
    def _get_formatted_git_url(exercise: models.Exercise, rel_path: str) -> str:
        return f'/git/{exercise.course.id}/{exercise.number}.git/{rel_path}'

    def _send_git_request(
            self,
            username: str,
            method_name: str,
            url: str,
            data=None,
            service=None,
            password=conftest.FAKE_PASSWORD,
    ):
        client = webapp.test_client()
        encoded_credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()
        headers = (
            ('Authorization', f'Basic {encoded_credentials}'),
        )
        query_string = {'service': service} if service is not None else None

        # patch the REPOSITORY_FOLDER to make new repository every test
        with mock.patch('lms.lmsweb.views.REPOSITORY_FOLDER', self.temp_folder):
            return getattr(client, method_name)(url, query_string=query_string, headers=headers, data=data)

    def test_not_authorized_access(self, exercise: models.Exercise, student_user: models.User):
        client = conftest.get_logged_user(student_user.username)
        response = client.get(self._get_formatted_git_url(exercise, self.INFO_URL))
        assert response.status_code == 401

    def test_not_existing_user(self, exercise: models.Exercise):
        response = self._send_git_request(
            username='not-exists',
            method_name=self.GET_METHOD,
            url=self._get_formatted_git_url(exercise, self.INFO_URL),
        )
        assert response.status_code == 401

    def test_invalid_user_password(self, exercise: models.Exercise, student_user: models.User):
        response = self._send_git_request(
            username=student_user.username,
            method_name=self.GET_METHOD,
            url=self._get_formatted_git_url(exercise, self.INFO_URL),
            password='not real password'
        )
        assert response.status_code == 401

    def test_push_exercise(self, exercise: models.Exercise, student_user: models.User):
        git_receive_pack = 'git-receive-pack'
        conftest.create_usercourse(student_user, exercise.course)

        response = self._send_git_request(
            username=student_user.username,
            method_name=self.GET_METHOD,
            url=self._get_formatted_git_url(exercise, self.INFO_URL),
            service=git_receive_pack,
        )

        assert response.status_code == 200
        assert response.data.startswith(b'001f#')

        response = self._send_git_request(
            username=student_user.username,
            method_name=self.POST_METHOD,
            url=self._get_formatted_git_url(exercise, git_receive_pack),
            data=POST_NEW_REPOSITORY_BUFFER,
        )
        assert response.status_code == 200
        assert response.data.startswith(b'0030\x01000eunpack ok\n0019ok refs/heads/master\n00000000')

    def test_get_exercise(self, exercise: models.Exercise, student_user: models.User):
        git_upload_pack = 'git-upload-pack'
        self.test_push_exercise(exercise, student_user)
        response = self._send_git_request(
            username=student_user.username,
            method_name=self.GET_METHOD,
            url=self._get_formatted_git_url(exercise, self.INFO_URL),
            service=git_upload_pack,
        )
        assert response.status_code == 200
        assert response.data.startswith(b'001e# service=git-upload-pack')

        response = self._send_git_request(
            username=student_user.username,
            method_name=self.POST_METHOD,
            url=self._get_formatted_git_url(exercise, git_upload_pack),
            data=POST_CLONE_REPOSITORY_BUFFER,
        )
        assert response.status_code == 200
        assert response.data.startswith(b'0008NAK\n0023\x02Enumerating objects: 3, done.')
