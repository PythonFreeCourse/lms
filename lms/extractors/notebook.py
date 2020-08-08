from itertools import chain
import json
from operator import itemgetter
from typing import Any, Dict, Iterator, List, Tuple

from lms.extractors.base import Extractor


NotebookJson = Dict[str, Any]
Cell = Dict[str, Any]


class Notebook(Extractor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            cells = self._get_code_cells()
            self.cells = chain([next(cells)], cells)  # Run the generator
        except (json.JSONDecodeError, KeyError):
            self.is_json = False
        else:
            self.is_json = True

    def can_extract(self) -> bool:
        return self.is_json

    def _get_code_cells(self) -> Iterator[Cell]:
        notebook = json.loads(self.to_extract)
        cells = notebook['cells']
        yield from filter(self._is_code_cell, cells)

    @staticmethod
    def _is_code_cell(cell: Cell) -> bool:
        return (
            cell.get('cell_type', '') == 'code'
            and bool(cell.get('source'))
        )

    @classmethod
    def get_exercise(cls, to_extract: Cell) -> Tuple[str, str]:
        code: List[str] = to_extract.get('source', [])
        return cls._clean(code)

    def get_exercises(self) -> Iterator[Tuple[str, str]]:
        """Yield exercise ID and code from notebook."""
        yield from filter(itemgetter(0), map(self.get_exercise, self.cells))
