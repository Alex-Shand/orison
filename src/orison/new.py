import threading
import time
import uuid
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path
from typing import no_type_check

from . import sh, util
from .bootstrap import build_iso
from .command import Arg, cmd
from .destroy import destroy_internal
from .launch import launch as _launch
from .system_manifest import CpuModel, SystemManifest
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
    no_update=Arg.switch(
        help="If passed do not attempt to install windows updates after VM creation"
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
    no_update: bool,
    desktop: bool,
    icon: str | None,
    snapshot: bool,
    shared: bool,
) -> None:
    assert template is None, "not implemented"
    if name == "system":
        raise SystemExit("Cannot call a VM system")
    if not desktop and icon is not None:
        raise SystemExit("--icon can only be passed with --desktop")
    if not desktop and shared:
        raise SystemExit("Cannot pass launch options without --desktop")

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
    resources = build_iso(vm_manifest)
    _create_vm(vm_manifest, system_manifest, resources)
    _finalize_config(vm_manifest, system_manifest)
    vm_manifest.mark_complete()

    # Launch the VM to install updates. We don't really have a good way of
    # detecting when this is done so we just leave it, you have to shut it down
    # yourself
    if not no_update:
        threading.Thread(
            target=_install_update_hook, kwargs={"name": f"{vm_manifest.name} [shared]"}
        ).start()
        _launch(vm_manifest.name, shared=True)


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
        # Apparently this setting improves passthrough performance and stability
        "--machine",
        "q35",
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


@no_type_check  # MyPy hates ElementTree
def _finalize_config(vm_manifest: VmManifest, system_manifest: SystemManifest) -> None:
    domain = sh.virsh("dumpxml", vm_manifest.name)
    domain = ET.fromstring(domain)

    # Enable shared memory
    memory_backing = ET.SubElement(domain, "memoryBacking")
    ET.SubElement(memory_backing, "source", type="memfd")
    ET.SubElement(memory_backing, "access", mode="shared")

    # Mark the CPU config as non-migratable. This exposes every possible
    # property of the host CPU to the guest
    cpu = domain.find("cpu")
    cpu.attrib["migratable"] = "off"

    # Add CPU specific virtualization flags
    ET.SubElement(
        cpu,
        "feature",
        policy="require",
        name=system_manifest.cpu_model.hardware_virtualization_flag(),
    )

    devices = domain.find("devices")

    # Remove all the extra disks used during install and set the primary disk
    # driver to virtio
    for disk in devices.findall("disk"):
        name = disk.find("target").attrib["dev"]
        # Primary disk
        if name == "sda":
            disk.find("target").attrib["dev"] = "vda"
            disk.find("target").attrib["bus"] = "virtio"
            # virsh will generate an appropriate address when the xml is
            # imported
            disk.remove(disk.find("address"))
        else:
            devices.remove(disk)

    # Switch the network model to virtio
    devices.find("interface").find("model").attrib["type"] = "virtio"

    # Mount the host's home directory inside the VM
    filesystem = ET.SubElement(
        devices, "filesystem", type="mount", accessmode="passthrough"
    )
    ET.SubElement(filesystem, "driver", type="virtiofs")
    ET.SubElement(filesystem, "source", dir=f"/var/home/{util.USERNAME}")
    ET.SubElement(filesystem, "target", dir="BAZZITE")

    # Add a new Channel for the qemu guest agent
    channel = ET.SubElement(devices, "channel", type="unix")
    ET.SubElement(channel, "target", type="virtio", name="org.qemu.guest_agent.0")

    # Add dedicated RNG hardware
    rng = ET.SubElement(devices, "rng", model="virtio")
    backend = ET.SubElement(rng, "backend", model="random")
    backend.text = "/dev/urandom"

    # Replace default HyperV features with (apparently) better ones
    hyperv = domain.find("features").find("hyperv")
    hyperv.attrib["mode"] = "custom"
    hyperv.clear()
    ET.SubElement(hyperv, "relaxed", state="on")
    ET.SubElement(hyperv, "vapic", state="on")
    ET.SubElement(hyperv, "spinlocks", state="on", retries="8191")
    ET.SubElement(hyperv, "vpindex", state="on")
    ET.SubElement(hyperv, "runtime", state="on")
    ET.SubElement(hyperv, "synic", state="on")
    stimer = ET.SubElement(hyperv, "stimer", state="on")
    ET.SubElement(stimer, "direct", state="on")
    ET.SubElement(hyperv, "reset", state="on")
    ET.SubElement(hyperv, "vendor_id", state="on", value="KVM Hv")
    ET.SubElement(hyperv, "frequencies", state="on")
    ET.SubElement(hyperv, "reenlightenment", state="on")
    ET.SubElement(hyperv, "tlbflush", state="on")
    ET.SubElement(hyperv, "ipi", state="on")
    if system_manifest.cpu_model is CpuModel.INTEL:
        ET.SubElement(hyperv, "evmcs", state="on")

    _prepare_shared(vm_manifest, deepcopy(domain))
    _prepare_selfish(vm_manifest, system_manifest, domain)


@no_type_check
def _prepare_shared(vm_manifest, domain):
    # Shared should be a different VM in libvirt so we need to update the name
    # and uuid
    domain.find("name").text = f"{vm_manifest.name} [shared]"
    domain.find("uuid").text = str(uuid.uuid4())
    _define_vm(vm_manifest, domain)


@no_type_check
def _prepare_selfish(vm_manifest, system_manifest, domain):
    # Allocate the VM 80% of system ram, rounded down to the nearest GB
    memory_kb = system_manifest.vm_memory_gb() * 1024 * 1024
    domain.find("memory").text = memory_kb
    domain.find("currentMemory").text = memory_kb

    # Remove the old memory source and replace it with a hugepage backing
    memory_backing = domain.find('memoryBacking')
    memory_backing.remove(memory_backing.find('source'))
    hugepages = ET.SubElement(memory_backing, 'hugepages')
    ET.SubElement(hugepages, 'page', size=1024*1024, unit='KiB')

    devices = domain.find("devices")

    # Remove the spice based display
    for channel in devices.findall("channel"):
        if channel.attrib["type"] == "spicevmc":
            devices.remove(channel)
    devices.remove(devices.find("graphics"))

    # # Add a VNC server
    # graphics = ET.SubElement(
    #     devices, "graphics", type="vnc", port="-1", autoport="yes", listen="0.0.0.0"
    # )
    # ET.SubElement(graphics, "listen", type="address", address="0.0.0.0")

    # Disable spice audio
    devices.find("audio").attrib["type"] = "none"

    # Remove default USB redirects
    for redirdev in devices.findall("redirdev"):
        devices.remove(redirdev)

    # Bind any GPUs we found into the VM (they will have to be available at the
    # point the VM actually boots or the PC will lock up)
    for addr in system_manifest.pci_addresses:
        hostdev = ET.SubElement(
            devices, "hostdev", mode="subsystem", type="pci", managed="yes"
        )
        source = ET.SubElement(hostdev, "source")
        ET.SubElement(
            source,
            "address",
            domain=f"0x{addr.domain}",
            bus=f"0x{addr.bus}",
            slot=f"0x{addr.slot}",
            function=f"0x{addr.function}",
        )

    _define_vm(vm_manifest, domain)


@no_type_check
def _define_vm(vm_manifest, domain):
    xml = f"/tmp/{vm_manifest.name}.xml"
    with open(xml, "wb") as f:
        f.write(ET.tostring(domain))

    sh.virsh("define", "--file", xml, "--validate", capture=False)


def _install_update_hook(*, name: str) -> None:
    while not sh.guest_ping(name):
        time.sleep(1)
    sh.qemu(name, "Z:\\.orison\\Install-Hook.ps1")
    sh.virsh("reboot", "--mode", "agent", check=False)
