import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from types import FrameType, PackageType
from typing import Any, Callable
import importlib
import inspect
import pkgutil



@dataclass
class Arg:
    _positional: bool
    short: str | None
    help: str | None

    @staticmethod
    def positional(*, help: str | None = None) -> "Arg":
        return Arg(_positional=True, short=None, help=help)

    @staticmethod
    def named(*, short: str | None = None, help: str | None = None) -> "Arg":
        return Arg(_positional=False, short=short, help=help)


def cmd[**P, T](
    f: Callable[P, T] | None = None, **argspec: Arg
) -> Callable[P, T] | Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(f: Callable[P, T]) -> Callable[P, T]:
        f._argspec = argspec  # type: ignore # pylint: disable=protected-access
        return f

    if f is not None:
        return decorator(f)
    return decorator


def run(package: PackageType) -> None:
    pass
    # entrypoints = {
    #     name.replace("_", "-"): entrypoint
    #     for name, entrypoint in _parent_frame().f_globals.items()
    #     if _is_entrypoint(entrypoint)
    # }

    # parser = ArgumentParser()
    # subparsers = parser.add_subparsers(
    #     required=True,
    #     dest="_entrypoint",
    #     metavar=f'{{{", ".join(entrypoints.keys())}}}',
    # )
    # for cmd in entrypoints:
    #     _apply_argspec(
    #         subparsers.add_parser(cmd),
    #         entrypoints[cmd]._argspec,  # pylint: disable=protected-access
    #     )

    # args = parser.parse_args()

    # entrypoint = entrypoints[args._entrypoint]  # pylint: disable=protected-access
    # del args._entrypoint
    # entrypoint(**vars(args))


def _get_all_functions(package: PackageType) -> None:
    functions = []
    for _, modname, ispkg in pkgutil.walk_packages(
        package.__path__, package.__name__ + "."
    ):
        module = importlib.import_module(modname)
        for name, func in inspect.getmembers(module, inspect.isfunction):
            funcs.append(func)
    return funcs


def _parent_frame() -> FrameType:
    return sys._getframe().f_back.f_back  # type: ignore # pylint: disable=protected-access


def _is_entrypoint(function: Any) -> bool:
    if not callable(function):
        return False
    return hasattr(function, "_argspec")


def _apply_argspec(parser: ArgumentParser, argspec: dict[str, Arg]) -> None:
    for name, spec in argspec.items():
        if spec._positional:  # pylint: disable=protected-access
            arg = [name]
        elif spec.short is not None:
            arg = [f"-{spec.short}", f"--{name}"]
        else:
            arg = [f"--{name}"]
        parser.add_argument(*arg, help=spec.help)
