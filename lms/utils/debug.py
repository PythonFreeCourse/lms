import multiprocessing
import os


def is_enabled() -> bool:
    debug_env = os.getenv('DEBUGGER')
    return debug_env in {'1', 'True'}


def start() -> None:
    pid = multiprocessing.current_process().pid
    if pid is not None and pid > 1:
        import debugpy  # type: ignore  # NOQA

        debugpy.listen(('0.0.0.0', 5678))
