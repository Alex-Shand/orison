import os
from pathlib import Path

IMAGE_DIR = Path("/var/lib/libvirt/images")
USERNAME = os.environ.get("SUDO_USER")
RESOURCE_DIR = Path(os.path.expanduser(f"~{USERNAME}")).resolve() / ".orison"
EXE = Path(__file__).resolve().parent.parent
SERVICE_NAME = "orison.service"
HOOK_PATH = Path("/etc/libvirt/hooks/qemu")
TRANSPARENT_HUGEPAGE_PATH = Path("/sys/kernel/mm/transparent_hugepage/enabled")


def config_dir() -> Path:
    path = Path.home() / ".orison"
    path.mkdir(parents=True, exist_ok=True)
    return path
