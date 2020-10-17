from flask import abort, jsonify


class LmsError(Exception):
    pass


class UploadError(LmsError):
    pass


class AlreadyExists(LmsError):
    pass


class BadUploadFile(LmsError):
    pass


class FileSizeError(LmsError):
    pass


class NotValidRequest(LmsError):  # Error 400
    pass


class ForbiddenPermission(LmsError):  # Error 403
    pass


class ResourceNotFound(LmsError):  # Error 404
    pass


class UnprocessableRequest(LmsError):  # Error 422
    pass


def fail(status_code: int, error_msg: str):
    data = {
        'status': 'failed',
        'msg': error_msg,
    }
    response = jsonify(data)
    response.status_code = status_code
    return abort(response)
