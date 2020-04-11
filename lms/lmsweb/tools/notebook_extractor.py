import difflib
import re
from typing import Any, Iterator, Dict, Iterable, Tuple, List

Notebook = Dict[str, Any]
Cell = Dict[str, Any]
_UPLOAD_KEYWORD = 'Upload'
ASSIGNMENT_NAME_REGEX = re.compile(fr'{_UPLOAD_KEYWORD}\s+\d+', re.IGNORECASE)
_MATCHER_THRESHOLD = 0.7


def get_similarity(header: str) -> Tuple[str, str]:
    if not header:
        return '', ''
    _header_parts = header.split()
    if len(_header_parts) < 2:
        err = (
            f'invalid "{_UPLOAD_KEYWORD}" - got "{header}" - '
            f'maybe you forgot the word {_UPLOAD_KEYWORD} or the exercise number?'
        )
        return '', err
    _upload_header = _header_parts[0].lower()
    s_matcher = difflib.SequenceMatcher(None, _upload_header, _UPLOAD_KEYWORD.lower())
    typo_msg = (
        f"You have a typo in {header} - "
        f"did you mean {_UPLOAD_KEYWORD}?"
    )
    if _MATCHER_THRESHOLD < s_matcher.ratio() < 1:
        return '', typo_msg

    return '', ''


def is_code_cell(cell: Cell):
    return cell.get('cell_type', '') == 'code' and cell.get('source', [])


def get_code_cells(notebook_data: Notebook) -> Iterator[Cell]:
    cells = (cell for cell in notebook_data.get('cells', []))
    return filter(is_code_cell, cells)


def get_exercise(cell: Cell) -> Tuple[str, str]:
    # return exercise_id, exercise_code for matched exercises
    # return error message in second argument
    # if nothing found return both empty
    code: List[str] = cell.get('source', [])
    if not code:
        return '', ''
    header = code[0].strip()
    if not header.startswith('#'):
        return '', ''
    header = header.strip('#').strip()
    if ASSIGNMENT_NAME_REGEX.fullmatch(header):
        return header.split()[1], ''.join(code[1:])
    return get_similarity(header)


def get_exercises_from_code_cells(
    cells: Iterable[Cell]
) -> Iterator[Tuple[str, str]]:
    return filter(lambda x: x[1], map(get_exercise, (c for c in cells)))


def extract_exercises(notebook_data: Notebook) -> Iterator[Tuple[str, str]]:
    """yield exercise ID and relevant code for that exercise from notebook"""
    if 'cells' not in notebook_data:
        raise ValueError("Invalid file format - must be ipynb")

    cells = get_code_cells(notebook_data)
    return get_exercises_from_code_cells(cells)
