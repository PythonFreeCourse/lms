import os
import subprocess
import typing
import logging

import flask

from lms.lmsdb import models

_logger = logging.getLogger(__name__)


class _GitOperation(typing.NamedTuple):
    response_content_type: str
    service_command: typing.List[str]
    supported: bool
    format_response: typing.Optional[typing.Callable]


class GitService:
    def __init__(
            self,
            current_user_id: int,
            exercise_id: int,
            request: flask.Request,
            base_repository_folder,
    ):
        self._base_repository_folder = base_repository_folder
        self._current_user_id = current_user_id
        self._exercise_id = exercise_id
        self._request = request

    @property
    def project_name(self):
        return f'{self._exercise_id}-{self._current_user_id}'

    def handle_operation(self) -> flask.Response:
        git_operation = self._extract_git_operation()
        repository_folder = os.path.join(self._base_repository_folder, self.project_name)

        first_time_repository = not os.path.exists(repository_folder)
        if first_time_repository:
            os.makedirs(repository_folder)
            p = subprocess.Popen(
                args=['git', 'init', '--bare'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=repository_folder,
            )
            assert p.wait() == 0

        if not git_operation.supported:
            raise EnvironmentError

        p = subprocess.Popen(
            args=git_operation.service_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self._base_repository_folder,
        )
        data_out, _ = p.communicate(self._request.data, 20)

        if git_operation.format_response:
            data_out = git_operation.format_response(data_out)

        res = self.build_response(data_out, git_operation)
        return res

    @staticmethod
    def build_response(data_out: bytes, git_operation: _GitOperation) -> flask.Response:
        res = flask.make_response(data_out)
        res.headers['Expires'] = 'Fri, 01 Jan 1980 00:00:00 GMT'
        res.headers['Pragma'] = 'no-cache'
        res.headers['Cache-Control'] = 'no-cache, max-age=0, must-revalidate'
        res.headers['Content-Type'] = git_operation.response_content_type
        return res

    def _extract_git_operation(self) -> _GitOperation:
        upload_pack_command = 'git-upload-pack'
        receive_pack_command = 'git-receive-pack'
        supported = True
        format_response = False

        if self._request.path.endswith(upload_pack_command):
            content_type = 'application/x-git-upload-pack-result'
            service_command = [upload_pack_command, '--stateless-rpc', self.project_name]

        elif self._request.path.endswith(receive_pack_command):
            content_type = 'application/x-git-receive-pack-result'
            service_command = [receive_pack_command, '--stateless-rpc', self.project_name]

        elif self._request.path.endswith('/info/refs'):
            service_name = self._request.args.get('service')
            service_command = [service_name, '--stateless-rpc', '--advertise-refs', self.project_name]
            content_type = f'application/x-{service_name}-advertisement'
            supported = service_name in [upload_pack_command, receive_pack_command]

            def format_response_callback(response_bytes):
                packet = f'# service={service_name}\n'
                length = len(packet) + 4
                prefix = "{:04x}".format(length & 0xFFFF)

                data = (prefix + packet + '0000').encode()
                data += response_bytes
                return data

            format_response = format_response_callback

        else:
            _logger.error('Failed to find the git command for route %s', self._request.path)
            raise NotImplementedError

        return _GitOperation(
            response_content_type=content_type,
            service_command=service_command,
            supported=supported,
            format_response=format_response,
        )
