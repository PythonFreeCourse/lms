from abc import abstractmethod
import re
from re import IGNORECASE
import string
from typing import (
    Any, ClassVar, Iterator, Pattern, Sequence, Tuple, Union, cast,
)

from loguru import logger

Text = Union[str, bytes]
CodeFile = Union[Sequence[Text], str, bytes]


class Extractor:
    UPLOAD_TITLE: ClassVar[Pattern] = re.compile(r'Upload\s+(\d+)', IGNORECASE)

    def __init__(self, to_extract: Any):
        self.to_extract = to_extract

    @staticmethod
    def _convert_to_text(code: CodeFile) -> str:
        if isinstance(code, (list, tuple, set)):
            if code and isinstance(code[0], bytes):
                code = b''.join(code)
                return code.decode(errors='replace')
            return ''.join(code)

        if code and isinstance(code, bytes):
            return code.decode(errors='replace')

        assert isinstance(code, str)  # noqa: S101
        return code

    @classmethod
    def _split_header(cls, code: CodeFile) -> Tuple[str, str]:
        code = cast(str, cls._convert_to_text(code))

        clean_text = code.strip('#' + string.whitespace)
        first_line_end = clean_text.find('\n')
        first_line = clean_text[:first_line_end].strip()
        code_lines = clean_text[first_line_end:].strip()

        logger.debug(f'Upload title: {first_line}')
        return first_line, code_lines

    @classmethod
    def _clean(cls, code: Union[Sequence, str]) -> Tuple[str, str]:
        first_line, code_text = cls._split_header(code)
        upload_title = cls.UPLOAD_TITLE.fullmatch(first_line)
        if upload_title:
            return upload_title.group(1), code_text

        logger.debug(f'Unmatched title: {first_line}')
        return '', ''

    @abstractmethod
    def can_extract(self) -> bool:
        pass

    @classmethod
    @abstractmethod
    def get_exercise(cls, to_extract: Any) -> Tuple[str, str]:
        pass

    @abstractmethod
    def get_exercises(self):
        pass

    def __iter__(self) -> Iterator[Tuple[str, str]]:
        for cls in self.__class__.__subclasses__():
            extractor = cls(to_extract=self.to_extract)
            if extractor.can_extract():
                yield from extractor.get_exercises()
