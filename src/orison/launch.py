from .command import Arg, cmd


@cmd(
    name=Arg.positional(help="The VM to launch"),
    shared=Arg.switch(
        short="s",
        help="By default orison assumes that the launched VM is the only one running & it will "
        "exclusively claim resources leaving the host just enough for the host to run "
        "virtualization tasks. With --shared the VM will claim fewer resources and nothing "
        "exclusively so that the host is still usable and other VMs can be launched. This option "
        "will cause worse performance of the VM.",
    ),
)
def launch() -> None:
    pass
