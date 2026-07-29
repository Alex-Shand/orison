from .command import Arg, cmd
from .launch import launch as _launch
from .system_manifest import SystemManifest

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
    desktop: bool,
    icon: str | None,
    snapshot: bool,
    shared: bool,
) -> None:
    assert template is None and not snapshot and not shared, "not implemented"
    if not desktop and icon is not None:
        raise SystemExit("--icon can only be passed with --desktop")
    print(f"New: {name}")
    system_manifest = SystemManifest.load()
    print(system_manifest)
