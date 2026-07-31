import getpass
import os
import shutil
from pathlib import Path

from .. import sh, util
from ..vm_manifest import VmManifest
from . import _util


def build_iso(vm_manifest: VmManifest, template: str | None) -> Path:
    print(util.RESOURCE_DIR)

    if template is None:
        template = "orison.template.default"

    build_dir = Path(f"/tmp/orison/template/{vm_manifest.name}")
    build_dir.mkdir(parents=True, exist_ok=True)

    # If the chosen template isn't a bundled one copy any resources it
    # has into the build directory
    if not template.startswith("orison.template"):
        path = util.RESOURCE_DIR / template
        sh.run(
            "rsync",
            "-a",
            "--delete",
            "--info=progress2",
            f"{path}/",
            str(build_dir),
            capture=False,
        )
        run_cmd = "path bootstrap.py"
    else:
        run_cmd = f"module {template}"

    # We also put a copy of orison into the resource ISO so the bootstrap
    # process can use it
    utils_dir = build_dir / "_orison"
    utils_dir.mkdir(parents=True, exist_ok=True)
    exe = Path(__file__).resolve().parent.parent.parent
    shutil.copy(exe, utils_dir / "orison.pyz")

    # And the winsfp.msi which is used by the default bootstrap template
    shutil.copy(util.RESOURCE_DIR / "winsfp.msi", utils_dir / "winsfp.msi")

    # Generate all of the bootstrap utilities
    _generate_utilities(build_dir, utils_dir, run_cmd)

    # Compile the ISO
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


def _generate_utilities(build_dir: Path, utils_dir: Path, run_cmd: str) -> None:
    _write_file(build_dir / "bootstrap.ps1", _util.BOOTSTRAP.format(run_cmd=run_cmd))
    _write_file(utils_dir / "hook.py", _util.HOOK)


def _write_file(target: Path, contents: str) -> None:
    with open(target, "w", encoding="utf8") as f:
        f.write(contents)
