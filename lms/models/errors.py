from flask import abort, jsonify


class LmsError(Exception):
    pass


class UploadError(LmsError):
    pass


class AlreadyExists(LmsError):
    pass


class BadUploadFile(LmsError):
    pass


def fail(status_code: int, error_msg: str):
    data = {
        'status': 'failed',
        'msg': error_msg,
    }
    response = jsonify(data)
    response.status_code = status_code
    return abort(response)
