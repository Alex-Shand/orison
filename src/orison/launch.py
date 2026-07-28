from .command import Arg, cmd


@cmd(
    name=Arg.positional(help="The VM to launch"),
    gpu_passthrough=Arg.switch(short="g", help="Launch with GPU passthrough"),
    require_huge_page=Arg.switch(
        help="If the hugepage optimisation isn't enabled or the VM can't claim the reserved huge "
        "pages it will fail to launch instead of falling back to normal memory"
    ),
)
def launch() -> None:
    pass
