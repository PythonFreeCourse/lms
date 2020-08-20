from typing import Iterator, List, Tuple

from lms.extractors.base import Extractor, File


class Pyfile(Extractor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def can_extract(self) -> bool:
        return True

    def get_exercise(self, to_extract: str) -> Tuple[int, List[File]]:
        exercise_id, content = self._clean(to_extract)
        return (exercise_id, [File('/main.py', content)])

    def get_exercises(self) -> Iterator[Tuple[int, List[File]]]:
        exercise_id, files = self.get_exercise(self.file_content)
        if exercise_id and files and files[0].code:
            yield (exercise_id, files)
