import os
from pathlib import Path

IMAGE_DIR = Path("/var/lib/libvirt/images")
USERNAME = os.environ.get('SUDO_USER')
# RESOURCE_DIR = (
#     Path(os.path.expanduser(f"~{os.environ.get('SUDO_USER')}")).resolve() / ".orison"
# )


def config_dir() -> Path:
    path = Path.home() / ".orison"
    path.mkdir(parents=True, exist_ok=True)
    return path
