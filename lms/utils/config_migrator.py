import ast
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple


LINES_RANGE = Tuple[int, Optional[int]]


def extract_assignment(assignment: ast.Assign) -> Tuple[str, LINES_RANGE]:
    targets = ', '.join(
        t.id for t in assignment.targets if isinstance(t, ast.Name)
    )
    lines_range = (assignment.lineno - 1, assignment.end_lineno)
    return (targets, lines_range)


def get_config_assignments(config: Path) -> Dict[str, LINES_RANGE]:
    ast_nodes = ast.walk(ast.parse(config.read_text()))
    assignments = dict(
        extract_assignment(ast_node)
        for ast_node in ast_nodes
        if isinstance(ast_node, ast.Assign)
    )
    return assignments


def get_missing_config(file: Path, lines: Iterable[LINES_RANGE]) -> str:
    content = file.read_text().splitlines()
    lines_to_add = (content[start:end or len(content)] for start, end in lines)
    return '\n'.join(line for block in lines_to_add for line in block)


def migrate(config: Path, template_config: Path) -> None:
    config_assignments = get_config_assignments(config)
    template_assignments = get_config_assignments(template_config)
    new_keys = template_assignments.keys() - config_assignments.keys()

    new_lines = (v for k, v in template_assignments.items() if k in new_keys)
    missing_configuration = get_missing_config(template_config, new_lines)
    with config.open('a') as main_config:
        main_config.write(f'\n{missing_configuration}')


# TODO: Support slicing on the left side of the assignment.  # NOQA
# TODO: Support override of specific configuration value.u   # NOQA
