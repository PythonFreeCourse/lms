import itertools
import json
import re
from typing import Any, Dict, Iterator, List, Tuple

from lms.extractors.base import Extractor, File
from lms.utils.files import ALLOWED_EXTENSIONS
from lms.utils.log import log


NotebookJson = Dict[str, Any]
Cell = Dict[str, Any]


class Notebook(Extractor):
    POSSIBLE_JSON_EXCEPTIONS = (
        json.JSONDecodeError, KeyError, StopIteration, UnicodeDecodeError,
    )
    TYPE_LINE_PREFIX = re.compile(r'type:\s+(\w+)', re.IGNORECASE)
    DEFAULT_FILE_TYPE = 'py'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            cells = self._get_code_cells()
            # Triggers StopIteration if `cells` is empty (see example below).
            first_cell = next(cells)
            self.cells = itertools.chain([first_cell], cells)
        except self.POSSIBLE_JSON_EXCEPTIONS:
            self.is_json = False
        else:
            self.is_json = True

    def can_extract(self) -> bool:
        return self.is_json

    @staticmethod
    def _is_code_cell(cell: Cell) -> bool:
        return (
            cell.get('cell_type', '') == 'code'
            and bool(cell.get('source'))
        )

    def _get_code_cells(self) -> Iterator[Cell]:
        notebook = json.loads(self.file_content)
        cells = notebook['cells']
        yield from filter(self._is_code_cell, cells)

    def _get_file_type(self, code: str) -> Tuple[str, str]:
        type_line, code_lines = self._split_header(code)
        file_type_match = self.TYPE_LINE_PREFIX.fullmatch(type_line)

        if file_type_match:
            file_type = file_type_match.group(1)
            if file_type not in ALLOWED_EXTENSIONS:
                file_type = self.DEFAULT_FILE_TYPE
            log.debug(f'File type: {file_type}.')
            return code_lines, file_type

        log.debug('No file type defined.')
        return code, self.DEFAULT_FILE_TYPE

    def get_exercise(self, to_extract: Cell) -> Tuple[int, List[File]]:
        code: List[str] = to_extract.get('source', [])
        exercise_id, clean_code = self._clean(code)
        clean_code, ext = self._get_file_type(clean_code)
        return (exercise_id, [File(f'/main.{ext}', clean_code)])

    def get_exercises(self) -> Iterator[Tuple[int, List[File]]]:
        """Yield exercise ID and code from notebook."""
        for cell in self.cells:
            exercise_id, files = self.get_exercise(cell)
            if exercise_id and files and files[0].code:
                yield (exercise_id, files)


if __name__ == '__main__':
    # An example of how the itertools.chain + next() trick works
    cells = iter([1, 2, 3])
    assert list(itertools.chain([next(cells)], cells)) == [1, 2, 3]
    try:
        list(itertools.chain([next(cells)], cells))
        raise AssertionError()
    except StopIteration:
        pass
