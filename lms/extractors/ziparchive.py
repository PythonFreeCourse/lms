from typing import Any, Iterator, List, Tuple

from lms.extractors.base import Extractor, File


class Ziparchive(Extractor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def can_extract(self) -> bool:
        pass

    @classmethod
    def get_exercise(cls, to_extract: bytes) -> Tuple[int, List[File]]:
        pass

    def get_exercises(self) -> Iterator[Tuple[int, List[File]]]:
        pass
