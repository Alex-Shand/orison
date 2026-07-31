from pathlib import Path

IMAGE_DIR = Path("/var/lib/libvirt/images")
RESOURCE_DIR = Path(os.path.expanduser(f'~{getpass.getuser()}')).resolve()

def config_dir() -> Path:
    path = Path.home() / ".orison"
    path.mkdir(parents=True, exist_ok=True)
    return path
