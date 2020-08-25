import pathlib
from tempfile import SpooledTemporaryFile

from werkzeug.datastructures import FileStorage

import lms.extractors.base as extractor
import lms.extractors.ziparchive as zipfilearchive


samples_dir = pathlib.Path(__file__).parent / 'samples'

file1 = open(f'{samples_dir}/code1.py')
PYFILE1 = FileStorage(file1)

file2 = open(f'{samples_dir}/code2.py')
PYFILE2 = FileStorage(file2)

file3 = open(f'{samples_dir}/code2.py', encoding='utf-8')
PYFILE3 = FileStorage(file3)

file4 = open(f'{samples_dir}/upload-1-2.ipynb', encoding='utf-8')
IPYNB = FileStorage(file4)

file5 = open(f'{samples_dir}/Upload_123.zip', 'br')
spooled = SpooledTemporaryFile()
spooled.write(file5.read())
ZIPFILE = FileStorage(spooled)
ZIPFILE.filename = 'Upload_123.zip'
file5.close()

PYFILES = (PYFILE1, PYFILE2, PYFILE3)


class TestExtractor:
    def test_notebook(self):
        results = list(extractor.Extractor(IPYNB))
        assert len(results) == 2
        assert results[0][0] == 3141
        assert results[1][0] == 2
        solution = extractor.Extractor(PYFILE2).file_content
        assert results[0][1][0].code == solution.replace('# Upload 3141', '').strip()

        file4.close()

    def test_py(self):
        for file in PYFILES:
            solutions = list(extractor.Extractor(file))
            assert len(solutions) == 1
            assert solutions[0][0] == 3141

        file1.close()
        file2.close()
        file3.close()

    def test_zip(self):
        result = zipfilearchive.Ziparchive(to_extract=ZIPFILE)
        exercises = list(result.get_exercises())[0][1]
        assert len(exercises) == 8