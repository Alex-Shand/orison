import os

from . import sh
from .command import cmd


@cmd
def selfish_end() -> None:
    os.remove("/etc/libvirt/hooks/qemu")
    sh.run(
        "rpm-ostree",
        "kargs",
        "--delete-if-present=hugepagesz=1G",
        "--delete-if-present=default_hugepagesz=1G",
        "--delete-if-present=hugepages=25",
    )
    with open("/sys/kernel/mm/transparent_hugepage/enabled", "w", encoding="utf8") as f:
        f.write("never")
    sh.run("sysctl", "vm.stat_interval=1")
    sh.run("sysctl", "-w", "kernel.watchdog=1")
    sh.run("systemctl", "reboot", check=False, capture=False, audit=True)
