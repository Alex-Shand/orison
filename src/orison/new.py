from .command import Arg, cmd
from .launch import launch as _launch

_LAUNCH_ARGS = _launch._argspec  # type: ignore # pylint: disable=protected-access
_LAUNCH_ARGS = {
    name: arg.undocumented() for name, arg in _LAUNCH_ARGS.items() if name != "name"
}


@cmd(
    name=Arg.positional(help="The name of the VM to create"),
    template=Arg.named(short="t", help="Custom bootstrap template"),
    desktop=Arg.named(
        short="d",
        help="Create a .desktop file to launch the VM. If --desktop is passed then any options on "
        "orison launch can also be passed and the generated .desktop file will use them",
    ),
    icon=Arg.named(
        short="i",
        help="If --desktop is passed sets the icon of the generated .desktop file. Error otherwise",
    ),
    **_LAUNCH_ARGS
)
def new() -> None:
    print("New")
