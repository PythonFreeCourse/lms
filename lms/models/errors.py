class LmsError(Exception):
    pass


class UploadError(LmsError):
    pass


class AlreadyExists(LmsError):
    pass
