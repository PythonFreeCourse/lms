from typing import Iterator, List, Tuple

from lms.extractors.base import Extractor, File


class Pyfile(Extractor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def can_extract(self) -> bool:
        return True

    @classmethod
    def get_exercise(cls, to_extract: str) -> Tuple[int, List[File]]:
        exercise_id, content = cls._clean(to_extract)
        return (exercise_id, [File('/main.py', content)])

    def get_exercises(self) -> Iterator[Tuple[int, List[File]]]:
        exercise_id, files = self.get_exercise(self.file_content)
        if files and files[0].code:
            yield (exercise_id, files)
