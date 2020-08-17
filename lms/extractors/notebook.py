import itertools
import json
from typing import Any, Dict, Iterator, List, Tuple

from lms.extractors.base import Extractor, File


NotebookJson = Dict[str, Any]
Cell = Dict[str, Any]


class Notebook(Extractor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            cells = self._get_code_cells()
            # Mandatory to run the generator
            self.cells = itertools.chain([next(cells)], cells)
        except (json.JSONDecodeError, KeyError):
            self.is_json = False
        else:
            self.is_json = True

    def can_extract(self) -> bool:
        return self.is_json

    def _get_code_cells(self) -> Iterator[Cell]:
        notebook = json.loads(self.file_content)
        cells = notebook['cells']
        yield from filter(self._is_code_cell, cells)

    @staticmethod
    def _is_code_cell(cell: Cell) -> bool:
        return (
            cell.get('cell_type', '') == 'code'
            and bool(cell.get('source'))
        )

    @classmethod
    def get_exercise(cls, to_extract: Cell) -> Tuple[int, List[File]]:
        code: List[str] = to_extract.get('source', [])
        exercise_id, clean_code = cls._clean(code)
        return (exercise_id, [File('/main.py', clean_code)])

    def get_exercises(self) -> Iterator[Tuple[int, List[File]]]:
        """Yield exercise ID and code from notebook."""
        for cell in self.cells:
            exercise_id, files = self.get_exercise(cell)
            if files and files[0].code:
                yield (exercise_id, files)
