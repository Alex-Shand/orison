from . import sh
from .command import Arg, cmd
from .vm_manifest import VmManifest


@cmd(name=Arg.positional(help="The VM to destroy"))
def destroy(name: str) -> None:
    manifest = VmManifest.try_load(name)
    if manifest is None:
        return
    destroy_internal(manifest)


def destroy_internal(manifest: VmManifest) -> None:
    sh.run("virsh", "undefine", manifest.name, check=False)
    manifest.disk.unlink(missing_ok=True)
