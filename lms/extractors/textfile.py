from typing import Iterator, List, Tuple

from lms.extractors.base import Extractor, File
from lms.models.errors import BadUploadFile


TEXTCHARS = set(bytes(
    {7, 8, 9, 10, 12, 13, 27}
    | set(range(0x20, 0x100)) - {0x7f},
))


class Textfile(Extractor):
    ALLOWED_EXTENSIONS = {'css', 'html', 'js', 'py', 'sql'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filename_no_ext, _, self.ext = self.filename.rpartition('.')

    def can_extract(self) -> bool:
        if self.ext not in self.ALLOWED_EXTENSIONS:
            return False
        if isinstance(self.file_content, str):
            return True
        return all(c in TEXTCHARS for c in self.file_content)

    def get_exercise(self, to_extract: str) -> Tuple[int, List[File]]:
        exercise_id, content = self._clean(to_extract)
        if self.filename and not exercise_id:
            exercise_id, _ = self._clean(self.filename_no_ext)
            content = to_extract
        if not exercise_id:
            raise BadUploadFile("Can't resolve exercise id", self.filename)

        return (exercise_id, [File(f'/main.{self.ext}', content)])

    def get_exercises(self) -> Iterator[Tuple[int, List[File]]]:
        exercise_id, files = self.get_exercise(self.file_content)
        if exercise_id and files and files[0].code:
            yield (exercise_id, files)
