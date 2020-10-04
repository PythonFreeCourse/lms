import fnmatch
import os
import pathlib
from typing import Iterator, List, Set, Text, Tuple
from zipfile import BadZipFile, ZipFile

from lms.extractors.base import Extractor, File
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
    def _extract(archive: ZipFile, filename: str, dirname: str = '') -> File:
        with archive.open(filename) as current_file:
            log.debug(f'Extracting from archive: {filename}')
            code = current_file.read()
        decoded = code.decode('utf-8', errors='replace').replace('\x00', '')
        filename = filename[len(dirname):]
        return File(path=f'/{filename}', code=decoded)

    def get_files(
        self, archive: ZipFile, filenames: List[Text], dirname: str = '',
    ) -> Iterator[File]:
        unwanted_files = self.get_unwanted_files(filenames)
        yield from (
            self._extract(archive, filename, dirname)
            for filename in filenames
            if (
                filename.startswith(dirname)
                and filename not in unwanted_files
                and filename != dirname
            )
        )

    def get_exercises_by_dirs(
        self, archive: ZipFile, filenames: List[Text],
    ) -> Iterator[Tuple[int, List[File]]]:
        for dirname in filenames:
            if len(dirname.strip(os.path.sep).split(os.path.sep)) == 1:
                # Checking if the dirname is in the first dir in the zipfile
                parent_name, _ = os.path.split(dirname)
                exercise_id, _ = self._clean(parent_name)
                if exercise_id:
                    files = list(self.get_files(archive, filenames, dirname))

                    yield exercise_id, files

    def get_exercise(self, file: ZipFile) -> Iterator[Tuple[int, List[File]]]:
        assert self.filename is not None
        exercise_id, _ = self._clean(self.filename.rpartition('.')[0])

        with file as archive:
            filenames = archive.namelist()
            if exercise_id:
                files = list(self.get_files(archive, filenames))
                yield exercise_id, files

            else:
                yield from self.get_exercises_by_dirs(archive, filenames)

    def get_exercises(self) -> Iterator[Tuple[int, List[File]]]:
        for exercise_id, files in self.get_exercise(self.archive):
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
