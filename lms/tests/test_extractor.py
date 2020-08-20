import pathlib

import pytest

import lms.extractors.base as extractor


PYFILE1 = '# Upload 3141\n\nNormal exercise'
PYFILE2 = """
            
                         
# Upload 3141

Normal exercise
להלהלה


קצת מילים, @!%^%^& וסימנים מוזרים
רווח בסוף yay
       
"""
PYFILE3 = PYFILE2.encode('utf-8')
PYFILES = (PYFILE1, PYFILE2, PYFILE3)

samples_dir = pathlib.Path(__file__).parent / 'samples'
IPYNB = (samples_dir / 'upload-1-2.ipynb').read_bytes()


@pytest.mark.skip('!!!Yam FIX ME!!!!')
class TestExtractor:
    def test_notebook(self):
        results = list(extractor.Extractor(IPYNB))
        assert len(results) == 2
        assert results[0][0] == '3141'
        assert results[1][0] == '2'
        assert results[0][1] == PYFILE2.replace('# Upload 3141', '').strip()

    def test_py(self):
        for file in PYFILES:
            solutions = list(extractor.Extractor(file))
            assert len(solutions) == 1
            assert solutions[0][0] == '3141'
