import getpass
import os
import shutil
from pathlib import Path

from .. import sh, util
from ..vm_manifest import VmManifest
from . import _util


def build_iso(vm_manifest: VmManifest) -> Path:
    if template is None:
        template = "orison.template.default"

    build_dir = Path(f"/tmp/orison/template/{vm_manifest.name}")
    build_dir.mkdir(parents=True, exist_ok=True)

    exe = Path(__file__).resolve().parent.parent.parent
    shutil.copy(exe, utils_dir / "orison.pyz")

    shutil.copy(util.RESOURCE_DIR / "winsfp.msi", utils_dir / "winsfp.msi")

    _generate_utilities(build_dir, utils_dir, run_cmd)

    output = util.IMAGE_DIR / f"{vm_manifest.name}-resources.iso"
    sh.run(
        "mkisofs",
        "-iso-level",
        "4",
        "-R",
        "-V",
        "RESOURCES",
        "-o",
        util.IMAGE_DIR / f"{vm_manifest.name}-resources.iso",
        build_dir,
        capture=False,
    )
    return output


def _generate_utilities(build_dir: Path) -> None:
    _write_file(build_dir / "bootstrap.ps1", _util.BOOTSTRAP)
    _write_file(build_dir / "hook.py", _util.HOOK)


def _write_file(target: Path, contents: str) -> None:
    with open(target, "w", encoding="utf8") as f:
        f.write(contents)
