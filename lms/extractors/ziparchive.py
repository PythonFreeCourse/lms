import fnmatch
import pathlib
from typing import Iterator, List, Set, Tuple
from zipfile import BadZipFile, ZipFile

from lms.extractors.base import Extractor, File
from lms.models.errors import BadUploadFile
from lms.utils.log import log


GITIGNORE_FILE = pathlib.Path(__file__).parent / 'ignorefiles.txt'


class Ziparchive(Extractor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_zipfile = (
            self.filename is not None
            and self.filename.endswith('.zip')
        )
        if not self.is_zipfile:
            return

        try:
            self.archive = ZipFile(self.to_extract.stream._file)
        except BadZipFile:
            self.is_zipfile = False

    def can_extract(self) -> bool:
        return self.is_zipfile

    @staticmethod
    def _extract(archive: ZipFile, filename: str) -> File:
        with archive.open(filename) as current_file:
            log.debug(f'Extracting from archive: {filename}')
            code = current_file.read()
        decoded = code.decode('utf-8', errors='replace').replace('\x00', '')
        return File(path=f'/{filename}', code=decoded)

    def get_exercise(self, file: ZipFile) -> Tuple[int, List[File]]:
        assert self.filename is not None
        exercise_id, _ = self._clean(self.filename.rpartition('.')[0])
        if not exercise_id:
            raise BadUploadFile('Invalid zip name', self.filename)

        with file as archive:
            namelist = archive.namelist()
            unwanted_files = self.get_unwanted_files(namelist)

            files = [
                self._extract(archive, filename)
                for filename in namelist
                if filename not in unwanted_files
            ]

        return exercise_id, files

    def get_exercises(self) -> Iterator[Tuple[int, List[File]]]:
        exercise_id, files = self.get_exercise(self.archive)
        if exercise_id and files and any(file.code for file in files):
            yield (exercise_id, files)

    @staticmethod
    def get_unwanted_files_types() -> Iterator[str]:
        with open(GITIGNORE_FILE, 'r') as file:
            lines = file.read().splitlines()

        yield from (
            line.strip()
            for line in lines
            if line and not line.strip().startswith('#')
        )

    def get_unwanted_files(self, namelist: List[str]) -> Set:
        unwanted_files = set()
        for pattern in self.get_unwanted_files_types():
            unwanted_files.update(fnmatch.filter(namelist, pattern))
        return unwanted_files
