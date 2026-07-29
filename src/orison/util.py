from pathlib import Path


def config_dir() -> Path:
    path = Path.home() / ".orison"
    path.mkdir(parents=True, exist_ok=True)
    return path
