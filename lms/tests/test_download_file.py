from io import BytesIO
import os
from tempfile import SpooledTemporaryFile
from typing import Iterator
from zipfile import ZipFile

import pytest
from werkzeug.datastructures import FileStorage

from lms.extractors.base import File
from lms.lmsdb.models import Exercise, User
from lms.lmsweb import webapp
from lms.tests import conftest
from lms.utils import hashing


DOWNLOAD_FILE = os.path.join(conftest.SAMPLES_DIR, 'download_test.zip')


class TestDownloadSolution:
    def setup(self):
        self.zipfile_file = self.zipfile_file()
        self.zipfile_content = self.zipfile_file.read()

    def teardown(self):
        self.zipfile_file.close()

    @staticmethod
    def get_zip_files() -> Iterator[File]:
        with ZipFile(DOWNLOAD_FILE) as zip_file:
            for file_path in zip_file.namelist():
                with zip_file.open(file_path) as file_code:
                    yield File(file_path, file_code.read())

    def zipfile_file(self):
        return open(DOWNLOAD_FILE, 'br')

    def create_zipfile_storage(self):
        spooled = SpooledTemporaryFile()
        spooled.write(self.zipfile_content)
        zip_file_storage = FileStorage(spooled)
        zip_file_storage.filename = DOWNLOAD_FILE.rpartition(os.path.sep)[-1]
        return zip_file_storage

    @pytest.mark.skip('Should run with docker system access')
    def test_download_solution(
            self,
            exercise: Exercise,
            student_user: User,
    ):
        storage = self.create_zipfile_storage()
        hash_ = hashing.by_file(storage)
        conftest.create_solution(
            exercise=exercise,
            student_user=student_user,
            files=list(TestDownloadSolution.get_zip_files()),
            hash_=hash_,
        )
        client = webapp.test_client()
        client.post(
            '/login',
            data=dict(  # noqa: S106
                username=student_user.username,
                password='fake pass',
            ),
            follow_redirects=True,
        )
        download_response = client.get('/download/1')
        downloaded_bytes_file = BytesIO(download_response.data)
        downloaded_zipfile = ZipFile(downloaded_bytes_file, 'r')
        exist_zipfile = ZipFile(self.zipfile_file, 'r')
        for exist_filename, downloaded_filename in zip(
            exist_zipfile.namelist(), downloaded_zipfile.namelist(),
        ):
            assert exist_filename == downloaded_filename
            with exist_zipfile.open(exist_filename, 'r') as exist_file:
                with downloaded_zipfile.open(
                    downloaded_filename, 'r',
                ) as downloaded_file:
                    assert exist_file.read() == downloaded_file.read()
