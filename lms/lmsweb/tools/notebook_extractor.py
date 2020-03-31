import re
from typing import Any, Iterator, Dict, Iterable, Tuple, List


Notebook = Dict[str, Any]
Cell = Dict[str, Any]
ASSIGNMENT_NAME_REGEX = re.compile(r'Upload\s+\d+', re.IGNORECASE)


def is_code_cell(cell: Cell):
    return cell.get('cell_type', '') == 'code' and cell.get('source', [])


def get_code_cells(notebook_data: Notebook) -> Iterator[Cell]:
    cells = (cell for cell in notebook_data.get('cells', []))
    return filter(is_code_cell, cells)


def get_exercise(cell: Cell) -> Tuple[str, str]:
    code: List[str] = cell.get('source', [])
    if not code:
        return '', ''
    header = code[0].strip().strip('#').strip()
    if ASSIGNMENT_NAME_REGEX.fullmatch(header):
        return header.split()[1], ''.join(code[1:])
    return '', ''


def get_exercises_from_code_cells(
        cells: Iterable[Cell]
) -> Iterator[Tuple[str, str]]:
    return filter(lambda x: x[0], map(get_exercise, (c for c in cells)))


def extract_exercises(notebook_data: Notebook) -> Iterator[Tuple[str, str]]:
    """yield exercise ID and relevant code for that exercise from notebook"""
    if 'cells' not in notebook_data:
        raise ValueError("Invalid file format - must be ipynb")

    cells = get_code_cells(notebook_data)
    return get_exercises_from_code_cells(cells)
