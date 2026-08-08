import os

from . import sh, util
from .command import Arg, cmd

_SERVICE = """\
[Unit]
Description=orison launch script for vm {name}
After=multi-user.target
Wants=multi-user.target

[Service]
Type=oneshot
ExecStart=python {exe} selfish-launch {name}
RemainAfterExit=yes
User=root
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

_HOOK = """\
#!/usr/bin/env bash

NAME=$1
ACTION=$2
PHASE=$3

if [[ "$NAME" == "{name}" ]] && [[ "$ACTION" == "stopped" ]] && [[ "$PHASE" == "end" ]]; then
    python {exe} selfish-end
fi

"""


@cmd(
    name=Arg.positional(help="The VM to launch"),
    shared=Arg.switch(
        short="s",
        help="By default orison assumes that the launched VM is the only one running & it will "
        "exclusively claim resources leaving the host just enough to run virtualization tasks. "
        "With --shared the VM will claim fewer resources and nothing exclusively so that the host "
        "is still usable and other VMs can be launched. This option will cause worse performance "
        "of the VM.",
    ),
)
def launch(name: str, shared: bool) -> None:
    if shared:
        sh.virsh("start", f"{name} [shared]", capture=False)
        sh.run(
            "sudo",
            "-u",
            str(util.USERNAME),
            "/usr/bin/flatpak",
            "run",
            "--branch=stable",
            "--command=virt-manager",
            "org.virt_manager.virt-manager",
            "--connect",
            "qemu:///system",
            "--show-domain-console",
            f"{name} [shared]",
            capture=False,
        )
    else:
        with open("/etc/systemd/system/orison.service", "w", encoding="utf8") as f:
            f.write(_SERVICE.format(name=name, exe=util.EXE))
        with open("/etc/libvirt/hooks/qemu", "w", encoding="utf8") as f:
            f.write(_HOOK.format(name=name, exe=util.EXE))
        os.chmod("/etc/libvirt/hooks/qemu", 0o777)
        sh.run("systemctl", "enable", "orison.service", capture=False)
        sh.run("systemctl", "set-default", "multi-user.target", capture=False)

        sh.run(
            "rpm-ostree",
            "kargs",
            "--append-if-missing=hugepagesz=1G",
            "--append-if-missing=default_hugepagesz=1G",
            "--append-if-missing=hugepages=25",
            capture=False,
        )

        sh.run("systemctl", "reboot", capture=False)
