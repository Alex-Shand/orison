import os

from . import sh
from .command import Arg, cmd
from .system_manifest import SystemManifest


@cmd(name=Arg.positional(help="The VM to launch"))
def selfish_launch(name: str) -> None:
    # The VM is going to launch and claim the GPU & all the USB controllers
    # we've been able to find. That's going to make things difficult if the host
    # locks up at some point so the first thing we do is arange that the next
    # boot will go back to the host
    sh.run("systemctl", "disable", "orison.service", capture=False, audit=True)
    os.remove("/etc/systemd/system/orison.service")
    sh.run("systemctl", "set-default", "graphical.target", capture=False, audit=True)

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

    # # Load the VFIO Kernel Module
    sh.run("modprobe", "vfio-pci", capture=False, audit=True)

    # # Start the VM
    sh.virsh("start", name, capture=False, audit=True)
