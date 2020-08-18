import hashlib
from typing import IO, Union

from werkzeug.datastructures import FileStorage


def by_content(
    file_content: Union[bytes, str], *args, **kwargs,
) -> str:
    if not isinstance(file_content, bytes):
        file_content = file_content.encode('utf-8')

    hashed_code = hashlib.blake2b(digest_size=20)
    hashed_code.update(file_content)
    return hashed_code.hexdigest()


def by_file(
    file: Union[FileStorage, IO], *args, **kwargs,
) -> str:
    saved_location = file.tell()
    file.seek(0)

    file_content = file.read()
    if not isinstance(file_content, bytes):
        file_content = file_content.encode('utf-8')

    file_hash = by_content(file_content)
    file.seek(saved_location)

    return file_hash
