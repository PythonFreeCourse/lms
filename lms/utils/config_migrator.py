import ast
from io import TextIOWrapper
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def next_dict_key(d: Dict[Any, Any], key: Any) -> Optional[Any]:
    dict_iter = iter(d)
    for k in dict_iter:
        if k == key:
            return next(dict_iter, None)
    return None


def get_configs_values(
    config_path: Path, config_example_path: Path,
) -> Tuple[Set[str], Dict[str, int]]:
    config_values = {
        x.id for x in ast.walk(
            ast.parse(config_path.read_text()),
        )
        if isinstance(x, ast.Name) and x.col_offset == 0
    }
    config_example_values = {
        x.id: x.lineno for x in ast.walk(
            ast.parse(config_example_path.read_text()),
        )
        if isinstance(x, ast.Name) and x.col_offset == 0
    }
    return config_values, config_example_values


def write_missing_config_content(
    missing_lines: List[str], main_config: TextIOWrapper,
) -> None:
    for line in missing_lines:
        if line and not line.strip().startswith('#'):
            main_config.write(line + '\n')


def migrate(
    config_path: Path, config_example_path: Path,
) -> Set[str]:
    config_values, config_example_values = get_configs_values(
        config_path, config_example_path,
    )
    missing_values = set(config_example_values).difference(config_values)

    example_lines = config_example_path.read_text().splitlines()

    with open(str(config_path), 'a') as main_config:
        for missing_value in missing_values:
            starting_line = config_example_values[missing_value] - 1
            next_value = next_dict_key(config_example_values, missing_value)
            if next_value is not None:
                ending_line = config_example_values[next_value] - 1
                write_missing_config_content(
                    example_lines[starting_line:ending_line],
                    main_config,
                )
            else:
                write_missing_config_content(
                    example_lines[starting_line:], main_config,
                )

    return missing_values
