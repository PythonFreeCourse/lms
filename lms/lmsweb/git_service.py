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

    def __init__(
            self,
            user: models.User,
            exercise_id: int,
            request: flask.Request,
            base_repository_folder: str,
    ):
        self._base_repository_folder = base_repository_folder
        self._user = user
        self._exercise_id = exercise_id
        self._request = request

    @property
    def project_name(self) -> str:
        return f'{self._exercise_id}-{self._user.id}'

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
                exercise_id=self._exercise_id,
                files=files,
                solution_hash=solution_hash,
                user=self._user,
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
            log.error(
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
