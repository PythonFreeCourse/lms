from io import BufferedReader, BytesIO
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import Iterator, List, Tuple
from zipfile import ZipFile

from flask import json
import pytest
from werkzeug.datastructures import FileStorage

import lms.extractors.base as extractor
import lms.extractors.ziparchive as zipfilearchive
from lms.lmsdb.models import Course, User
from lms.models.errors import BadUploadFile
from tests import conftest
from tests.conftest import SAMPLES_DIR


class TestExtractor:
    IPYNB_NAME = 'upload-1-2.ipynb'
    IGNORE_FILES_ZIP_NAME = 'Upload_123.zip'
    IMAGE_NAME = 'Upload 3.jpg'
    IMAGE_NO_EXERCISE = 'bird.jpg'
    PY_DIFFERENT_COURSE = 'Upload 1.py'
    PY_NAMES = ('code1.py', 'code2.py', 'Upload 3141.py')
    PY_NO_EXERCISE = 'noexercise.py'
    ZIP_FILES = ('Upload_1.zip', 'zipfiletest.zip')
    ZIP_BOMB_FILE = 'zipbomb.zip'

    def setup(self):
        self.ipynb_file = self.ipynb_file()
        self.image_file = next(self.zip_files((self.IMAGE_NAME,)))
        self.image_no_exercise_file = next(self.zip_files(
            (self.IMAGE_NO_EXERCISE,),
        ))
        self.image_bytes_io = self.get_bytes_io_file(self.IMAGE_NAME)
        self.pyfile_different_course = self.get_bytes_io_file(
            self.PY_DIFFERENT_COURSE,
        )
        self.pyfiles_files = list(self.py_files(self.PY_NAMES))
        self.pyfile_no_exercise_file = next(self.py_files(
            (self.PY_NO_EXERCISE,),
        ))
        self.zipfile_file = next(self.zip_files((self.IGNORE_FILES_ZIP_NAME,)))
        self.ipynb_storage = FileStorage(self.ipynb_file)
        self.image_storage = FileStorage(self.image_file)
        self.image_no_exercise_storage = FileStorage(
            self.image_no_exercise_file,
        )
        self.pyfiles_storage = [
            FileStorage(pyfile)
            for pyfile in self.pyfiles_files
        ]
        self.pyfile_no_exercise_storage = FileStorage(
            self.pyfile_no_exercise_file,
        )
        self.zipfile_storage = self.create_zipfile_storage(
            self.zipfile_file, self.IGNORE_FILES_ZIP_NAME,
        )
        self.zipfiles_extractor_files = list(self.zip_files(self.ZIP_FILES))
        self.zipfiles_extractors_bytes_io = list(self.get_bytes_io_zip_files(
            self.zipfiles_extractor_files, self.ZIP_FILES,
        ))
        self.zipbomb_file_list = list(self.zip_files((self.ZIP_BOMB_FILE,)))
        self.zipbomb_bytes_io = next(self.get_bytes_io_zip_files(
            self.zipbomb_file_list, (self.ZIP_BOMB_FILE,),
        ))

    def teardown(self):
        self.ipynb_file.close()
        self.image_file.close()
        self.image_no_exercise_file.close()
        self.pyfile_no_exercise_file.close()
        self.zipfile_file.close()
        self.zipbomb_file_list[0].close()
        for py_file in self.pyfiles_files:
            py_file.close()
        for zip_file in self.zipfiles_extractor_files:
            zip_file.close()
        for bytes_io, _ in self.zipfiles_extractors_bytes_io:
            bytes_io.close()

    def ipynb_file(self):
        return open(Path(SAMPLES_DIR) / self.IPYNB_NAME, encoding='utf-8')

    @staticmethod
    def py_files(filenames: Iterator[str]):
        for file_name in filenames:
            yield open(Path(SAMPLES_DIR) / file_name)

    @staticmethod
    def get_bytes_io_file(file_name: str) -> Tuple[BytesIO, str]:
        with open(Path(SAMPLES_DIR) / file_name, 'br') as open_file:
            return BytesIO(open_file.read()), file_name

    @staticmethod
    def zip_files(filenames: Tuple[str, ...]) -> Iterator[BufferedReader]:
        for file_name in filenames:
            yield open(Path(SAMPLES_DIR) / file_name, 'br')

    @staticmethod
    def create_zipfile_storage(
        opened_file: BufferedReader, filename: str,
    ) -> FileStorage:
        spooled = SpooledTemporaryFile()
        spooled.write(opened_file.read())
        zip_file_storage = FileStorage(spooled)
        zip_file_storage.filename = filename
        opened_file.seek(0)
        return zip_file_storage

    @staticmethod
    def get_bytes_io_zip_files(
        files: List[BufferedReader], filesnames: Tuple[str, ...],
    ) -> Iterator[Tuple[BytesIO, str]]:
        for file, name in zip(files, filesnames):
            yield BytesIO(file.read()), name

    def get_zip_filenames(self):
        the_zip = ZipFile(f'{SAMPLES_DIR}/{self.IGNORE_FILES_ZIP_NAME}')
        return the_zip.namelist()

    def test_notebook(self):
        results = list(extractor.Extractor(self.ipynb_storage))
        assert len(results) == 5
        assert results[0][0] == 3141
        assert results[1][0] == 2
        assert results[2][1][0].path.endswith('.py')
        assert results[3][1][0].path.endswith('.html')
        assert results[4][1][0].path.endswith('.py')
        solution = extractor.Extractor(self.pyfiles_storage[1]).file_content
        solution = solution.replace('# Upload 3141', '')
        assert results[0][1][0].code == solution.strip()

    def test_image(self):
        results = list(extractor.Extractor(self.image_storage))
        assert len(results) == 1
        assert results[0][0] == 3

        with pytest.raises(BadUploadFile) as e_info:
            list(extractor.Extractor(self.image_no_exercise_storage))
        assert e_info.type is BadUploadFile
        assert e_info.value.args[0] == "Can't resolve exercise id."

    def test_py(self):
        for file in self.pyfiles_storage:
            solutions = list(extractor.Extractor(file))
            assert len(solutions) == 1
            assert solutions[0][0] == 3141

        with pytest.raises(BadUploadFile) as e_info:
            list(extractor.Extractor(self.pyfile_no_exercise_storage))
        assert e_info.type is BadUploadFile
        assert e_info.value.args[0] == "Can't resolve exercise id."

    def test_zip_ignore_files(self):
        result = zipfilearchive.Ziparchive(to_extract=self.zipfile_storage)
        exercises = list(result.get_exercises())[0][1]
        exercises_paths = [exercise.path for exercise in exercises]
        assert len(exercises) == 9
        original_zip_filenames = self.get_zip_filenames()

        assert all(
            '__pycache__/foo.py' not in exercise_path
            for exercise_path in exercises_paths
        )

        assert any(
            '__pycache__/foo.py' in filename
            for filename in original_zip_filenames
        )

        assert any(
            'bird.jpg' in exercise_path
            for exercise_path in exercises_paths
        )

    def test_zip(self, course: Course, student_user: User):
        conftest.create_exercise(course, 1)
        conftest.create_exercise(course, 2)
        conftest.create_exercise(course, 3)
        conftest.create_exercise(course, 4, is_archived=True)
        conftest.create_usercourse(student_user, course)

        client = conftest.get_logged_user(username=student_user.username)

        # Uploading a multiple zip solutions file
        upload_response = client.post(f'/upload/{course.id}', data={
            'file': self.zipfiles_extractors_bytes_io[1],
        })
        json_response_upload = json.loads(
            upload_response.get_data(as_text=True),
        )
        assert len(json_response_upload['exercise_misses']) == 1
        assert len(json_response_upload['exercise_matches']) == 2
        assert upload_response.status_code == 200

        # Uploading a zip file with a same solution exists in the previous zip
        second_upload_response = client.post(f'/upload/{course.id}', data={
            'file': self.zipfiles_extractors_bytes_io[0],
        })
        assert second_upload_response.status_code == 400

    def test_zip_bomb(self, course: Course, student_user: User):
        conftest.create_exercise(course, 1)

        client = conftest.get_logged_user(username=student_user.username)

        # Trying to upload a zipbomb file
        upload_response = client.post(f'/upload/{course.id}', data={
            'file': self.zipbomb_bytes_io,
        })
        assert upload_response.status_code == 413

    def test_upload_another_course(
        self,
        course: Course,
        student_user: User,
    ):
        course2 = conftest.create_course(index=1)
        conftest.create_exercise(course2, 1)
        conftest.create_usercourse(student_user, course)

        client = conftest.get_logged_user(username=student_user.username)
        fail_upload_response = client.post(f'/upload/{course2.id}', data={
            'file': self.pyfile_different_course,
        })
        assert fail_upload_response.status_code == 400

    def test_upload_invalid_exercise(
        self,
        course: Course,
        student_user: User,
    ):
        conftest.create_usercourse(student_user, course)

        client = conftest.get_logged_user(username=student_user.username)
        fail_upload_response = client.post(f'/upload/{course.id}', data={
            'file': self.image_bytes_io,
        })
        assert fail_upload_response.status_code == 400


    def test_upload_correct_course(
        self,
        course: Course,
        student_user: User,
    ):
        conftest.create_exercise(course, 1)
        conftest.create_usercourse(student_user, course)

        client = conftest.get_logged_user(username=student_user.username)
        success_upload_response = client.post(f'/upload/{course.id}', data={
            'file': self.pyfile_different_course,
        })
        assert success_upload_response.status_code == 200
