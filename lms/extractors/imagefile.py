import base64
import os
from typing import Iterator, List, Tuple

from lms.extractors.base import Extractor, File
from lms.models.errors import BadUploadFile
from lms.utils.files import ALLOWED_IMAGES_EXTENSIONS


class Imagefile(Extractor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filename_no_ext, _, self.ext = (
            os.path.basename(self.filename).rpartition('.')
        )

    def can_extract(self) -> bool:
        return self.ext.lower() in ALLOWED_IMAGES_EXTENSIONS

    def get_exercise(self, to_extract: bytes) -> Tuple[int, List[File]]:
        exercise_id = 0
        if self.filename:
            exercise_id, _ = self._clean(self.filename_no_ext)
        if not exercise_id:
            raise BadUploadFile("Can't resolve exercise id.", self.filename)

        decoded = base64.b64encode(to_extract)
        return (exercise_id, [File(f'/main.{self.ext.lower()}', decoded)])

    def get_exercises(self) -> Iterator[Tuple[int, List[File]]]:
        exercise_id, files = self.get_exercise(self.file_content)
        if exercise_id and files and files[0].code:
            yield (exercise_id, files)
