import abc
import os
import shutil
import tempfile
import uuid
import logging
import subprocess  # NOQA: S404

_logger = logging.getLogger(__name__)


class BaseExecutor:
    @classmethod
    def executor_name(cls):
        return cls.__name__

    def __enter__(self) -> 'BaseExecutor':
        return self

    @abc.abstractmethod
    def get_file_path(self, file_path):
        pass

    @abc.abstractmethod
    def run_on_executor(self, args: tuple):
        pass

    @abc.abstractmethod
    def write_file(self, file_path: str, content: str):
        pass

    @abc.abstractmethod
    def get_file(self, file_path: str):
        pass


class DockerExecutor(BaseExecutor):
    memory_limit = '100m'
    cpu_limit = '1'
    timeout_seconds = 20
    base_image = 'lms:latest'
    container_temp_dir = '/tmp'  # NOQA: S108

    def __init__(self):
        self._container_name = F'safe-{str(uuid.uuid4())[:10]}'

    def __enter__(self):
        args = (
            'docker', 'run', '-d', '--memory', self.memory_limit,
            '--cpus', self.cpu_limit, '--network', 'none',
            '--rm', '--name', self._container_name, self.base_image,
            'sleep', str(self.timeout_seconds),
        )
        _logger.info('Start executing safe container context with %s', args)
        subprocess.check_call(args)  # NOQA: S603
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        args = ('docker', 'rm', '-f', self._container_name)
        subprocess.call(args)  # NOQA: S603

    def get_file_path(self, file_path):
        return os.path.join(self.container_temp_dir, file_path)

    def run_on_executor(self, args: tuple):
        args = ('docker', 'exec', self._container_name) + args
        subprocess.call(args)  # NOQA: S603

    def write_file(self, file_path: str, content: str):
        with tempfile.NamedTemporaryFile('w') as temp_file:
            temp_file.write(content)
            temp_file.flush()
            full_path = os.path.join(self.container_temp_dir, file_path)
            args = (
                'docker', 'cp',
                temp_file.name, f'{self._container_name}:{full_path}',
            )
            subprocess.check_output(args)  # NOQA: S603

    def get_file(self, file_path: str):
        with tempfile.NamedTemporaryFile('w') as temp_file:
            temp_file.flush()
            container_path = os.path.join(self.container_temp_dir, file_path)
            docker_path = f'{self._container_name}:{container_path}'
            args = ('docker', 'cp', docker_path, temp_file.name)
            subprocess.check_output(args)  # NOQA: S603
            with open(temp_file.name, 'r') as file_reader:
                content = file_reader.read()
        return content


class SameProcessExecutor(BaseExecutor):
    """
    Used only for testing / local setups without docker
    """
    def __init__(self):
        self._cwd = tempfile.mkdtemp()

    def __exit__(self, exc_type, exc_val, exc_tb):
        shutil.rmtree(self._cwd)

    def get_file_path(self, file_path):
        return file_path

    def run_on_executor(self, args: tuple):
        subprocess.run(args, cwd=self._cwd)  # NOQA: S603

    def write_file(self, file_path: str, content: str):
        open(os.path.join(self._cwd, file_path), 'w').write(content)

    def get_file(self, file_path: str):
        return open(os.path.join(self._cwd, file_path), 'r').read()


__MAPPING = {
    executor.executor_name(): executor
    for executor in (
        DockerExecutor,
        SameProcessExecutor,
    )
}


def get_executor(executor_name=None) -> BaseExecutor:
    return __MAPPING.get(executor_name, DockerExecutor)()
