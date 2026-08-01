from pathlib import Path

from . import sh, util
from .command import Arg, cmd
from .destroy import destroy_internal
from .launch import launch as _launch
from .system_manifest import SystemManifest
from .template import build_iso
from .vm_manifest import VmManifest

_LAUNCH_ARGS = _launch._argspec  # type: ignore # pylint: disable=protected-access
_LAUNCH_ARGS = {
    name: arg.undocumented() for name, arg in _LAUNCH_ARGS.items() if name != "name"
}


@cmd(
    name=Arg.positional(help="The name of the VM to create"),
    template=Arg.named(short="t", help="Custom bootstrap template"),
    snapshot=Arg.switch(
        help="Create the VM with snapshot support. Note: This may negatively affect virtual hard "
        "disk performance"
    ),
    force=Arg.switch(
        short="f",
        help="If the VM already exists with the same settings re-create it instead of doing "
        "nothing",
    ),
    desktop=Arg.switch(
        short="d",
        help="Create a .desktop file to launch the VM. If --desktop is passed then any options on "
        "orison launch can also be passed and the generated .desktop file will use them",
    ),
    icon=Arg.named(
        short="i",
        help="If --desktop is passed sets the icon of the generated .desktop file. Error otherwise",
    ),
    **_LAUNCH_ARGS,
)
def new(
    name: str,
    template: str | None,
    force: bool,
    desktop: bool,
    icon: str | None,
    snapshot: bool,
    shared: bool,
) -> None:
    if name == "system":
        raise SystemExit("Cannot call a VM system")
    assert not shared, "not implemented"
    if not desktop and icon is not None:
        raise SystemExit("--icon can only be passed with --desktop")

    system_manifest = SystemManifest.load()
    old_vm_manifest = VmManifest.try_load(name)
    vm_manifest = VmManifest.create(name, snapshot)

    # If we've already created a VM with different settings we need to destroy it first. Several of
    # the configuration decisions we make prevent easy migration of existing VMs
    if old_vm_manifest is not None and vm_manifest != old_vm_manifest:
        destroy_internal(old_vm_manifest)
        old_vm_manifest = None

    # If we've created the VM with the same settings before:
    # If --force is passed we delete it and re-create
    # If the creation didn't complete successfully we delete it and re-create
    # If neither of the above is true we bail
    if old_vm_manifest is not None and vm_manifest == old_vm_manifest:
        if force or not vm_manifest.complete:
            destroy_internal(vm_manifest)
        else:
            print(f"VM {vm_manifest.name} already exists")
            return

    _create_disk(vm_manifest.disk)
    resources = build_iso(vm_manifest, template)
    _create_vm(vm_manifest, system_manifest, resources)


def _create_disk(disk: Path) -> None:
    format = disk.suffix[1:]
    # These files are created sparse so it won't actually consume 200GB immediately
    options = "size=200G"
    if format == "qcow2":
        # Makes the initial file slightly larger but improves write performance
        options += ",preallocation=metadata"
    sh.run("qemu-img", "create", "-f", format, "-o", options, disk, capture=False)


def _create_vm(
    vm_manifest: VmManifest, system_manifest: SystemManifest, resources: Path
) -> None:
    # We explicitly provide the CPU topology to the guest because performance will be degraded if
    # Windows misdetects the it & later we're going to explicitly reserve specific host CPUs
    # to provide to the guest. The host needs to keep 2 CPUs for virtualization tasks, if the CPU
    # is hyperthreaded this only requires one core TODO: --shared VMs should use less
    threads = system_manifest.cpu_topology.threads
    cores = system_manifest.cpu_topology.cores - (2 if threads == 1 else 1)
    # The guest sees one VCPU per host CPU on the cores assigned to it
    vcpus = cores * threads

    sh.run(
        "virt-install",
        "--name",
        vm_manifest.name,
        "--os-variant=win10",
        # BIOS boot is slightly slower than UEFI but it doesn't affect runtime performance and
        # bypasses figuring out how TPM works
        "--boot",
        "uefi=off",
        # We start with 2GB of RAM (in MB), the minimum Windows 10 needs to function. This will
        # be changed later
        "--memory",
        str(2 * 1024),
        # Let the guest see the exact host CPU it's running on
        "--cpu",
        "host-passthrough",
        # The first value is the number of VCPUs provided to the guest.The other three describe
        # the CPU topology
        f"--vcpus={vcpus},sockets=1,cores={cores},threads={threads}",
        # Storage: sata is less efficient than virtio but Windows doesn't include virtio drivers by
        # default so we install them during bootstrap and change this later.
        # cache=writeback caches reads and writes instead of going all the way to the host FS every
        # time. Writes are processed on a separate IO thread (which we will pin to a dedicated CPU
        # core later). This improves performance with the minor risk that data is lost if the host
        # crashes before the write is committed to disk
        # io=threads configures threaded IO for the above
        # discard=unmap causes KVM to release unused blocks in the host filesystem. This is less to
        # do with performance (although it apparently does have an affect for SSDs), it prevents
        # the disk file from growing too big
        "--disk",
        f"path={vm_manifest.disk},bus=sata,cache=writeback,io=threads,discard=unmap",
        # Will never be used so won't occupy any actual disk space. Windows needs to see a VirtIO
        # disk while the driver installation is ongoing or it won't add the VirtIO drivers
        "--disk",
        f"path={util.IMAGE_DIR}/virtio-tmp.raw,bus=virtio,size=1,sparse=true,format=raw",
        # I think this is only relevant once we switch to virtio disks but adding it now doesn't
        # break anything
        "--controller",
        "type=scsi,model=virtio-scsi",
        # Installer
        "--cdrom",
        str(util.IMAGE_DIR / "orison-win10.iso"),
        # Bootstrap resources
        "--disk",
        f"path={resources},device=cdrom",
        # VirtIO drivers
        "--disk",
        f"path={util.IMAGE_DIR}/virtio-win.iso,device=cdrom",
        # Using virtio for the network model will also be more performant but again, we need
        # drivers for it
        "--network",
        "default,model=e1000e",
        # Graphics configuration, for a non-shared VM this is temporary for the bootstrap phase
        # TODO: --shared VMs will need to be more complicated about this
        "--graphics",
        "spice",
        capture=False,
    )
