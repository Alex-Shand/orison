import os
import subprocess

from . import typez


def run(
    *cmd: typez.PathLike,
    env: dict[str, str] | None = None,
    check: bool = True,
    capture: bool = True
) -> str:
    if env is not None:
        env = os.environ.copy() | env
    result = subprocess.run(cmd, check=check, env=env, capture_output=capture)
    if capture:
        return result.stdout.decode("utf8")
    return ""
