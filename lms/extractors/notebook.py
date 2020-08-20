import itertools
import json
from typing import Any, Dict, Iterator, List, Tuple

from lms.extractors.base import Extractor, File


NotebookJson = Dict[str, Any]
Cell = Dict[str, Any]


class Notebook(Extractor):
    POSSIBLE_JSON_EXCEPTIONS = (
        json.JSONDecodeError, KeyError, StopIteration, UnicodeDecodeError,
    )

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

    def get_exercise(self, to_extract: Cell) -> Tuple[int, List[File]]:
        code: List[str] = to_extract.get('source', [])
        exercise_id, clean_code = self._clean(code)
        return (exercise_id, [File('/main.py', clean_code)])

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
