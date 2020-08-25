from lms.tests.conftest import SAMPLES_DIR
from tempfile import SpooledTemporaryFile

from werkzeug.datastructures import FileStorage

import lms.extractors.base as extractor
import lms.extractors.ziparchive as zipfilearchive


class TestExtractor:
    IPYNB_NAME = 'upload-1-2.ipynb'
    ZIP_NAME = 'Upload_123.zip'
    PY_NAMES = ('code1.py', 'code2.py', 'code2.py')

    def setup(self):
        self.ipynb_file = self.ipynb_file()
        self.pyfiles_files = self.py_files()
        self.zipfile_file = self.zip_file()
        self.ipynb_storage = FileStorage(self.ipynb_file)
        self.pyfiles_storage = [
            FileStorage(pyfile)
            for pyfile in self.pyfiles_files
        ]
        self.zipfile_storage = self.create_zipfile_storage()

    def teardown(self):
        self.ipynb_file.close()
        self.zipfile_file.close()
        for py_file in self.pyfiles_files:
            py_file.close()

    def ipynb_file(self):
        return open(f'{SAMPLES_DIR}/{self.IPYNB_NAME}', encoding='utf-8')

    def py_files(self):
        for index, file_name in enumerate(self.PY_NAMES):
            if index == 2:
                yield open(f'{SAMPLES_DIR}/{file_name}', encoding='utf-8')
            else:
                yield open(f'{SAMPLES_DIR}/{file_name}')

    def zip_file(self):
        return open(f'{SAMPLES_DIR}/{self.ZIP_NAME}', 'br')

    def create_zipfile_storage(self):
        spooled = SpooledTemporaryFile()
        spooled.write(self.zipfile_file.read())
        zip_file_storage = FileStorage(spooled)
        zip_file_storage.filename = self.ZIP_NAME
        return zip_file_storage

    def test_notebook(self):
        results = list(extractor.Extractor(self.ipynb_storage))
        assert len(results) == 2
        assert results[0][0] == 3141
        assert results[1][0] == 2
        solution = extractor.Extractor(self.pyfiles_storage[1]).file_content
        solution = solution.replace('# Upload 3141', '')
        assert results[0][1][0].code == solution.strip()

    def test_py(self):
        for file in self.pyfiles_storage:
            solutions = list(extractor.Extractor(file))
            assert len(solutions) == 1
            assert solutions[0][0] == 3141

    def test_zip(self):
        result = zipfilearchive.Ziparchive(to_extract=self.zipfile_storage)
        exercises = list(result.get_exercises())[0][1]
        assert len(exercises) == 8
