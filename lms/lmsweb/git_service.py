import os
import shutil
import subprocess  # noqa: S404
import tempfile
import typing
import logging

import flask

from lms.lmsdb import models
from lms.models import upload
from lms.utils import hashing

_logger = logging.getLogger(__name__)


class _GitOperation(typing.NamedTuple):
    response_content_type: str
    service_command: typing.List[str]
    supported: bool
    format_response: typing.Optional[typing.Callable]
    contain_new_commits: bool


class GitService:
    def __init__(
            self,
            user: models.User,
            exercise_id: int,
            request: flask.Request,
            base_repository_folder,
    ):
        self._base_repository_folder = base_repository_folder
        self._user = user
        self._exercise_id = exercise_id
        self._request = request

    @property
    def project_name(self):
        return f'{self._exercise_id}-{self._user.id}'

    @property
    def repository_folder(self) -> str:
        return os.path.join(self._base_repository_folder, self.project_name)

    def handle_operation(self) -> flask.Response:
        git_operation = self._extract_git_operation()

        git_repository_folder = os.path.join(self.repository_folder, '.git')
        first_time_repository = not os.path.exists(git_repository_folder)
        if first_time_repository:
            os.makedirs(self.repository_folder, exist_ok=True)
            proc = subprocess.Popen(  # noqa: S603
                args=['git', 'init', '--bare'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.repository_folder,
            )
            if proc.wait() != 0:
                _logger.error(
                    'Failed to execute command. stdout=%s\nstderr=%s',
                    proc.stdout.read(), proc.stderr.read(),
                )
                raise EnvironmentError

        if not git_operation.supported:
            raise EnvironmentError

        proc = subprocess.Popen(  # noqa: S603
            args=git_operation.service_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self._base_repository_folder,
        )
        data_out, _ = proc.communicate(self._request.data, 20)

        if proc.wait() != 0:
            _logger.error(
                'Failed to execute command. stdout=%s\nstderr=%s',
                proc.stdout.read(), proc.stderr.read(),
            )
            raise EnvironmentError

        if git_operation.format_response:
            data_out = git_operation.format_response(data_out)

        if git_operation.contain_new_commits:
            files = self._load_files_from_repository()
            solution_hash = hashing.by_content(str(files))
            upload.upload_solution(
                exercise_id=self._exercise_id,
                files=files,
                solution_hash=solution_hash,
                user=self._user,
            )

        res = self.build_response(data_out, git_operation)
        return res

    @staticmethod
    def build_response(
            data_out: bytes,
            git_operation: _GitOperation,
    ) -> flask.Response:
        res = flask.make_response(data_out)
        res.headers['Expires'] = 'Fri, 01 Jan 1980 00:00:00 GMT'
        res.headers['Pragma'] = 'no-cache'
        res.headers['Cache-Control'] = 'no-cache, max-age=0, must-revalidate'
        res.headers['Content-Type'] = git_operation.response_content_type
        return res

    def _extract_git_operation(self) -> _GitOperation:
        stateless_rpc = '--stateless-rpc'
        advertise_refs = '--advertise-refs'
        upload_pack_command = 'git-upload-pack'
        receive_pack_command = 'git-receive-pack'
        allowed_commands = [upload_pack_command, receive_pack_command]

        supported = True
        format_response = False
        contain_new_commits = False

        if self._request.path.endswith(upload_pack_command):
            content_type = 'application/x-git-upload-pack-result'
            service_command = [
                upload_pack_command,
                stateless_rpc,
                self.project_name,
            ]

        elif self._request.path.endswith(receive_pack_command):
            content_type = 'application/x-git-receive-pack-result'
            service_command = [
                receive_pack_command,
                stateless_rpc,
                self.project_name,
            ]
            contain_new_commits = True

        elif self._request.path.endswith('/info/refs'):
            service_name = self._request.args.get('service')
            service_command = [
                service_name,
                stateless_rpc,
                advertise_refs,
                self.project_name,
            ]
            content_type = f'application/x-{service_name}-advertisement'

            supported = service_name in allowed_commands

            def format_response_callback(response_bytes: bytes) -> bytes:
                packet = f'# service={service_name}\n'
                length = len(packet) + 4
                prefix = '{:04x}'.format(length & 0xFFFF)

                data = (prefix + packet + '0000').encode()
                data += response_bytes
                return data

            format_response = format_response_callback

        else:
            _logger.error(
                'Failed to find the git command for route %s',
                self._request.path,
            )
            raise NotImplementedError

        return _GitOperation(
            response_content_type=content_type,
            service_command=service_command,
            supported=supported,
            format_response=format_response,
            contain_new_commits=contain_new_commits,
        )

    def _load_files_from_repository(self) -> typing.List[upload.File]:
        with tempfile.TemporaryDirectory() as tempdir:
            proc = subprocess.Popen(  # noqa: S603
                args=['git', 'clone', self.repository_folder, '.'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=tempdir,
            )
            return_code = proc.wait()
            if return_code != 0:
                _logger.error(
                    'Failed to execute command. stdout=%s\nstderr=%s',
                    proc.stdout.read(), proc.stderr.read(),
                )
                raise EnvironmentError
            to_return = []
            # remove git internal files
            shutil.rmtree(os.path.join(tempdir, '.git'))
            for root, _, files in os.walk(tempdir):
                for file in files:
                    upload_file = self._load_file(file, root, tempdir)
                    to_return.append(upload_file)
            return to_return

    @staticmethod
    def _load_file(file_path: str, root: str, tempdir: str) -> upload.File:
        with open(os.path.join(root, file_path)) as f:
            file_path = os.path.join(os.path.relpath(root, tempdir), file_path)
            upload_file = upload.File(path=file_path, code=f.read())
        return upload_file
