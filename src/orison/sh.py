import os
import subprocess

from . import typez


def run(
    *cmd: typez.PathLike,
    env: dict[str, str] | None = None,
    check: bool = True,
    capture: bool = True,
    audit: bool = False,
) -> str:
    if audit:
        print(f"Running: {cmd}")
    if env is not None:
        env = os.environ.copy() | env
    result = subprocess.run(cmd, check=check, env=env, capture_output=capture)
    if capture:
        return result.stdout.decode("utf8")
    return ""


def virsh(*cmd: str, check: bool = True, capture: bool = True, audit: bool = True) -> str:
    return run(
        "virsh", "--connect", "qemu:///system", *cmd, check=check, capture=capture, audit=audit
    )


def run_audit(*cmd: typez.PathLike) -> None:
    run(*cmd, check=False, capture=False, audit=True)


def msiexec(msi: str) -> None:
    run_audit("msiexec", "/i", msi, "/passive", "/norestart")


def pwsh(cmd: str) -> None:
    run_audit("powershell", "-C", f"&{{ {cmd} }}")
