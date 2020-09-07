from dataclasses import dataclass
import re
from re import IGNORECASE
import string
from typing import (
    Any, ClassVar, Iterator, List,
    Pattern, Sequence, Tuple, Union, cast,
)

from werkzeug.datastructures import FileStorage

from lms.utils.log import log


Text = Union[str, bytes]
CodeFile = Union[Sequence[Text], str, bytes]


@dataclass
class File:
    path: str
    code: Text


class Extractor:
    UPLOAD_TITLE: ClassVar[Pattern] = re.compile(r'Upload\s+(\d+)', IGNORECASE)

    def __init__(self, to_extract: FileStorage):
        self.to_extract = to_extract
        cursor_position = to_extract.tell()
        self.file_content = to_extract.read()
        to_extract.seek(cursor_position)
        self.filename = to_extract.filename

    @staticmethod
    def _convert_to_text(code: CodeFile) -> str:
        if isinstance(code, (list, tuple, set)):
            if code and isinstance(code[0], bytes):
                code = b''.join(code)
                return code.decode(errors='replace')
            return ''.join(code)

        if code and isinstance(code, bytes):
            return code.decode(errors='replace')

        assert isinstance(code, str)
        return code

    @classmethod
    def _split_header(cls, code: CodeFile) -> Tuple[str, str]:
        code = cast(str, cls._convert_to_text(code))

        clean_text = code.strip('#' + string.whitespace)
        first_line_end = clean_text.find('\n')
        if first_line_end == -1:
            first_line_end = len(clean_text)
        first_line = clean_text[:first_line_end].strip().replace('_', ' ')
        code_lines = clean_text[first_line_end:].strip()

        log.debug(f'Upload title: {first_line}')
        return first_line, code_lines

    @classmethod
    def _clean(cls, code: Union[Sequence, str]) -> Tuple[int, str]:
        first_line, code_text = cls._split_header(code)
        upload_title = cls.UPLOAD_TITLE.fullmatch(first_line)
        if upload_title:
            exercise_id = int(upload_title.group(1))
            return exercise_id, code_text

        return 0, ''

    def get_exercise(self, to_extract: Any) -> Tuple[int, List[File]]:
        raise NotImplementedError()

    def get_exercises(self) -> Iterator[Tuple[int, List[File]]]:
        raise NotImplementedError()

    def __iter__(self) -> Iterator[Tuple[int, List[File]]]:
        for cls in self.__class__.__subclasses__():
            log.debug(f'Trying extractor: {cls.__name__}')
            extractor = cls(to_extract=self.to_extract)
            if extractor.can_extract():
                for solution_id, files in extractor.get_exercises():
                    yield (solution_id, files)
