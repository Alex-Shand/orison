import os

from . import sh, util
from .command import cmd


@cmd
def selfish_end() -> None:
    try:
        os.remove(util.HOOK_PATH)
    except Exception as e:
        print(e)
        pass
    sh.run(
        "rpm-ostree",
        "kargs",
        "--delete-if-present=hugepagesz=1G",
        "--delete-if-present=default_hugepagesz=1G",
        "--delete=hugepages",
    )
    with open(util.TRANSPARENT_HUGEPAGE_PATH, "w", encoding="utf8") as f:
        f.write("madvise")
    sh.run("sysctl", "vm.stat_interval=1")
    sh.run("sysctl", "-w", "kernel.watchdog=1")
    sh.run("systemctl", "reboot", check=False, capture=False, audit=True)
