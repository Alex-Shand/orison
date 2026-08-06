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
        sh.virsh("start", name, capture=False)
        sh.run(
            "/usr/bin/flatpak",
            "run",
            "--branch=stable",
            "--command=virt-manager org.virt_manager.virt-manager",
            "--connect",
            "qemu:///system",
            "--show-domain-console",
            f'{name} [shared]',
            capture=False,
        )
        return

    with open("/etc/systemd/system/orison.service", "w", encoding="utf8") as f:
        f.write(_SERVICE.format(name=name, exe=util.EXE))
    sh.run("systemctl", "enable", "orison.service", capture=False)
    sh.run("systemctl", "set-default", "multi-user.target", capture=False)
    sh.run("systemctl", "reboot", capture=False)
