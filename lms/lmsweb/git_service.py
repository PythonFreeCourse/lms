import os
import shutil
import subprocess  # noqa: S404
import tempfile
import typing
import pathlib

import flask

from lms.lmsdb import models
from lms.models import upload
from lms.utils import hashing
from lms.utils.log import log


class _GitOperation(typing.NamedTuple):
    response_content_type: str
    service_command: typing.List[str]
    supported: bool
    format_response: typing.Optional[typing.Callable]
    contain_new_commits: bool


class GitService:
    _GIT_PROCESS_TIMEOUT = 20
    _GIT_VALID_EXIT_CODE = 0
    _STATELESS_RPC = '--stateless-rpc'
    _ADVERTISE_REFS = '--advertise-refs'
    _UPLOAD_COMMAND = 'git-upload-pack'
    _RECEIVE_COMMAND = 'git-receive-pack'
    _REFS_COMMAND = '/info/refs'

    def __init__(
            self,
            user: models.User,
            exercise_number: int,
            course_id: int,
            request: flask.Request,
            base_repository_folder: str,
    ):
        self._base_repository_folder = base_repository_folder
        self._user = user
        self._exercise_number = exercise_number
        self._course_id = course_id
        self._request = request

    @property
    def project_name(self) -> str:
        return f'{self._course_id}-{self._exercise_number}-{self._user.id}'

    @property
    def repository_folder(self) -> pathlib.Path:
        return pathlib.Path(self._base_repository_folder) / self.project_name

    def handle_operation(self) -> flask.Response:
        git_operation = self._extract_git_operation()
        repository_folder = self.repository_folder / 'config'

        new_repository = not repository_folder.exists()
        if new_repository:
            self._initialize_bare_repository()

        if not git_operation.supported:
            raise OSError

        data_out = self._execute_git_operation(git_operation)

        if git_operation.format_response:
            data_out = git_operation.format_response(data_out)

        if git_operation.contain_new_commits:
            files = self._load_files_from_repository()
            solution_hash = hashing.by_content(str(files))
            upload.upload_solution(
                course_id=self._course_id,
                exercise_number=self._exercise_number,
                files=files,
                solution_hash=solution_hash,
                user_id=self._user.id,
            )

        return self.build_response(data_out, git_operation)

    def _execute_command(
            self,
            args: typing.List[str],
            cwd: typing.Union[str, pathlib.Path],
            proc_input: typing.Optional[bytes] = None,
    ):
        proc = subprocess.Popen(  # noqa: S603
            args=args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
        )
        data_out, _ = proc.communicate(proc_input, self._GIT_PROCESS_TIMEOUT)
        operation_failed = proc.wait() != self._GIT_VALID_EXIT_CODE
        if operation_failed:
            log.error(
                'Failed to execute command %s. stdout=%s\nstderr=%s',
                args, proc.stdout.read(), proc.stderr.read(),
            )
            raise OSError
        return data_out

    def _execute_git_operation(self, git_operation: _GitOperation) -> bytes:
        return self._execute_command(
            args=git_operation.service_command,
            cwd=self._base_repository_folder,
            proc_input=self._request.data,
        )

    def _initialize_bare_repository(self) -> None:
        os.makedirs(self.repository_folder, exist_ok=True)
        self._execute_command(
            args=['git', 'init', '--bare'],
            cwd=self.repository_folder,
        )

    @staticmethod
    def build_response(
            data_out: bytes,
            git_operation: _GitOperation,
    ) -> flask.Response:
        res = flask.make_response(data_out)
        res.headers['Pragma'] = 'no-cache'
        res.headers['Cache-Control'] = 'no-cache, max-age=0, must-revalidate'
        res.headers['Content-Type'] = git_operation.response_content_type
        return res

    def _extract_git_operation(self) -> _GitOperation:
        if self._request.path.endswith(self._UPLOAD_COMMAND):
            return self._build_upload_operation()

        elif self._request.path.endswith(self._RECEIVE_COMMAND):
            return self._build_receive_operation()

        elif self._request.path.endswith(self._REFS_COMMAND):
            return self._build_refs_operation()

        else:
            log.error(
                'Failed to find the git command for route %s',
                self._request.path,
            )
            raise NotImplementedError

    def _build_refs_operation(self) -> _GitOperation:
        allowed_commands = [self._UPLOAD_COMMAND, self._RECEIVE_COMMAND]
        service_name = self._request.args.get('service')
        content_type = f'application/x-{service_name}-advertisement'
        supported = service_name in allowed_commands

        def format_response_callback(response_bytes: bytes) -> bytes:
            packet = f'# service={service_name}\n'
            length = len(packet) + 4
            prefix = '{:04x}'.format(length & 0xFFFF)

            data = (prefix + packet + '0000').encode()
            data += response_bytes
            return data

        return _GitOperation(
            response_content_type=content_type,
            service_command=[
                service_name,
                self._STATELESS_RPC,
                self._ADVERTISE_REFS,
                self.project_name,
            ],
            supported=supported,
            format_response=format_response_callback,
            contain_new_commits=False,
        )

    def _build_receive_operation(self) -> _GitOperation:
        return _GitOperation(
            response_content_type='application/x-git-receive-pack-result',
            service_command=[
                self._RECEIVE_COMMAND,
                self._STATELESS_RPC,
                self.project_name,
            ],
            supported=True,
            format_response=None,
            contain_new_commits=True,
        )

    def _build_upload_operation(self) -> _GitOperation:
        return _GitOperation(
            response_content_type='application/x-git-upload-pack-result',
            service_command=[
                self._UPLOAD_COMMAND,
                self._STATELESS_RPC,
                self.project_name,
            ],
            supported=True,
            format_response=None,
            contain_new_commits=False,
        )

    def _load_files_from_repository(self) -> typing.List[upload.File]:
        """
        Since the remote server is a git bare repository
        we need to 'clone' the bare repository to resolve the files.
        We are not changing the remote at any end - that is why we
        don't care about git files here.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            self._execute_command(
                args=['git', 'clone', self.repository_folder, '.'],
                cwd=tempdir,
            )
            to_return = []
            # remove git internal files
            shutil.rmtree(pathlib.Path(tempdir) / '.git')
            for root, _, files in os.walk(tempdir):
                for file in files:
                    upload_file = self._load_file(file, root, tempdir)
                    to_return.append(upload_file)
            return to_return

    @staticmethod
    def _load_file(file_name: str, root: str, tempdir: str) -> upload.File:
        file_path = str(pathlib.Path(root).relative_to(tempdir) / file_name)
        with open(pathlib.Path(root) / file_name) as f:
            upload_file = upload.File(path=file_path, code=f.read())
        return upload_file
