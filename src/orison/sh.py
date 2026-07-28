import os
import subprocess

from . import typez


def run(
    *cmd: typez.PathLike, env: dict[str, str] | None = None, check: bool = True
) -> None:
    if env is not None:
        env = os.environ.copy() | env
    subprocess.run(cmd, check=check, env=env)
