import os

from . import sh, util
from .command import Arg, cmd
from .system_manifest import SystemManifest


@cmd(name=Arg.positional(help="The VM to launch"))
def selfish_launch(name: str) -> None:
    # The VM is going to launch and claim the GPU & all the USB controllers
    # we've been able to find. That's going to make things difficult if the host
    # locks up at some point so the first thing we do is arange that the next
    # boot will go back to the host
    sh.run("systemctl", "disable", util.SERVICE_NAME, capture=False, audit=True)
    os.remove(f"/etc/systemd/system/{util.SERVICE_NAME}")
    sh.run("systemctl", "set-default", "graphical.target", capture=False, audit=True)

    # This prevents the kernel from using hugepages for normal memory
    # management. Not sure if it's useful since we've reserved ~80% of total ram
    # by this point anyway
    with open(util.TRANSPARENT_HUGEPAGE_PATH, "w", encoding="utf8") as f:
        f.write("never")

    # Magic thingys to decrease load on the host
    sh.run("sysctl", "vm.stat_interval=120")
    sh.run("sysctl", "-w", "kernel.watchdog=0")

    # We need to unbind all of the PCI addresses that we've used in the hostdev
    # tags in the VM definition so it can access them
    system_manifest = SystemManifest.load()
    for addr in system_manifest.pci_addresses:
        sh.virsh(
            "nodedev-detach",
            f"pci_{addr.domain}_{addr.bus}_{addr.slot}_{addr.function}",
            capture=False,
            audit=True,
        )

    # Load the VFIO Kernel Module
    sh.run("modprobe", "vfio-pci", capture=False, audit=True)

    # Start the VM
    sh.virsh("start", name, capture=False, audit=True)
