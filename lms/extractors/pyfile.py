from typing import Iterator, Tuple

from lms.extractors.base import Extractor


class Pyfile(Extractor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def can_extract(self) -> bool:
        return True

    @classmethod
    def get_exercise(cls, to_extract: str) -> Tuple[str, str]:
        return cls._clean(to_extract)

    def get_exercises(self) -> Iterator[Tuple[str, str]]:
        extractor = self.get_exercise(self.to_extract)
        if extractor and extractor[0]:
            yield extractor
