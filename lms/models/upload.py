import hashlib


def create_hash(file_content: bytes) -> str:
    if not isinstance(file_content, bytes):
        file_content = file_content.encode('utf-8')

    hashed_code = hashlib.blake2b(digest_size=20)
    hashed_code.update(file_content)
    return hashed_code.hexdigest()
