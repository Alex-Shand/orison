import base64
import json
import os
import subprocess
import time

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


def virsh(
    *cmd: str, check: bool = True, capture: bool = True, audit: bool = False
) -> str:
    return run(
        "virsh",
        "--connect",
        "qemu:///system",
        *cmd,
        check=check,
        capture=capture,
        audit=audit,
    )


def guest_ping(name: str) -> bool:
    result = subprocess.run(
        (
            "virsh",
            "--connect",
            "qemu:///system",
            "qemu-agent-command",
            name,
            json.dumps({"execute": "guest-ping"}),
        ),
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def qemu(name: str, cmd: str) -> str:
    result = virsh(
        "qemu-agent-command",
        name,
        json.dumps(
            {
                "execute": "guest-exec",
                "arguments": {
                    "path": "powershell.exe",
                    "arg": ["-C", cmd],
                    "capture-output": True,
                },
            }
        ),
        audit=True,
    )
    pid = json.loads(result)["return"]["pid"]
    while True:
        result = virsh(
            "qemu-agent-command",
            name,
            json.dumps({"execute": "guest-exec-status", "arguments": {"pid": pid}}),
        )
        result = json.loads(result)["return"]
        exited = result["exited"]
        if exited:
            break
        time.sleep(0.1)
    if "err-data" in result:
        print(base64.b64decode(result["err-data"]).decode("utf8"))
    if "out-data" in result:
        return base64.b64decode(result["out-data"]).decode("utf8")
    return ""


def run_audit(*cmd: typez.PathLike) -> None:
    run(*cmd, check=False, capture=False, audit=True)


def msiexec(msi: str) -> None:
    run_audit("msiexec", "/i", msi, "/passive", "/norestart")


def pwsh(cmd: str) -> None:
    run_audit("powershell", "-C", f"&{{ {cmd} }}")
