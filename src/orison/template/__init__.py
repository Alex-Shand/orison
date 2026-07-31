import shutil
from pathlib import Path

from .. import sh, util
from ..vm_manifest import VmManifest
from . import _util


def build_iso(vm_manifest: VmManifest, template: str | None) -> Path:
    if template is None:
        template = "orison.template.default"

    build_dir = Path(f"/tmp/orison/template/{vm_manifest.name}")
    build_dir.mkdir(parents=True, exist_ok=True)

    # If the chosen template isn't a bundled one copy any resources it
    # has into the build directory
    if not template.startswith("orison.template"):
        if not template.endswith("/"):
            template += "/"
        sh.run(
            "rsync",
            "-a",
            "--delete",
            "--info=progress2",
            template,
            str(build_dir),
            capture=False,
        )
        run_cmd = f"path {template}bootstrap.py"
    else:
        run_cmd = f"module {template}"

    # We also put a copy of orison into the resource ISO so the bootstrap process can use it
    exe = Path(__file__).resolve().parent.parent.parent
    shutil.copy(exe, build_dir / "orison.pyz")

    # Generate all of the bootstrap utilities
    _generate_utilities(build_dir, run_cmd)

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


def _generate_utilities(build_dir: Path, run_cmd: str) -> None:
    _write_file(build_dir / "bootstrap.ps1", _util.BOOTSTRAP.format(run_cmd=run_cmd))
    _write_file(build_dir / "hook.py", _util.HOOK)


def _write_file(target: Path, contents: str) -> None:
    with open(target, "w", encoding="utf8") as f:
        f.write(contents)
