import json
from dataclasses import dataclass
from pathlib import Path

from . import util
from .typez import JsonObj


@dataclass
class VmManifest:
    name: str
    disk: Path
    complete: bool

    @staticmethod
    def create(name: str, snapshot: bool) -> VmManifest:
        manifest = VmManifest(
            name=name,
            disk=util.IMAGE_DIR / (f"{name}.qcow2" if snapshot else f"{name}.raw"),
            complete=False,
        )
        manifest._write()  # pylint: disable=protected-access
        return manifest

    @staticmethod
    def try_load(name: str) -> VmManifest | None:
        path = manifest_path(name)
        try:
            with open(path, "r", encoding="utf8") as f:
                data = json.load(f)
            return VmManifest._from_json(data)
        except Exception:
            pass
        return None

    @staticmethod
    def _from_json(json: JsonObj) -> VmManifest:
        return VmManifest(
            name=json["name"], disk=Path(json["disk"]), complete=json["complete"]
        )

    def _write(self) -> None:
        as_json = {
            "name": self.name,
            "disk": str(self.disk),
            "complete": self.complete,
        }
        with open(manifest_path(self.name), "w", encoding="utf8") as f:
            json.dump(as_json, f)


def manifest_path(name: str) -> Path:
    return util.config_dir() / f"{name}.json"
