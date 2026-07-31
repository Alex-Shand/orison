import importlib
import inspect
import pkgutil
from argparse import SUPPRESS, ArgumentParser
from dataclasses import dataclass
from types import FunctionType, ModuleType
from typing import Any, Callable, Generator, overload


@dataclass
class Arg:
    _type: str
    short: str | None
    help: str | None

    @staticmethod
    def positional(*, help: str | None = None) -> Arg:
        return Arg(_type="positional", short=None, help=help)

    @staticmethod
    def named(*, short: str | None = None, help: str | None = None) -> Arg:
        return Arg(_type="named", short=short, help=help)

    @staticmethod
    def switch(*, short: str | None = None, help: str | None = None) -> Arg:
        return Arg(_type="switch", short=short, help=help)

    def undocumented(self) -> Arg:
        return Arg(_type=self._type, short=self.short, help=SUPPRESS)


@overload
def cmd[**P, T](f: Callable[P, T]) -> Callable[P, T]: ...


@overload
def cmd[**P, T](**argspec: Arg) -> Callable[[Callable[P, T]], Callable[P, T]]: ...


def cmd[**P, T](
    f: Any = None, **argspec: Arg
) -> Callable[P, T] | Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(f: Callable[P, T]) -> Callable[P, T]:
        f._argspec = argspec  # type: ignore # pylint: disable=protected-access
        return f

    if f is not None:
        return decorator(f)
    return decorator


def check(package: ModuleType) -> None:
    entrypoints = set()
    for name, entrypoint in _get_all_functions(package):
        if _is_entrypoint(name, entrypoint):
            name = name.replace("_", "-")
            if name in entrypoints:
                raise Exception(f"Duplicate entrypoint name {name}")
            entrypoints.add(name)


def run(package: ModuleType) -> None:
    entrypoints = {
        name.replace("_", "-"): entrypoint
        for name, entrypoint in _get_all_functions(package)
        if _is_entrypoint(name, entrypoint)
    }

    parser = ArgumentParser()
    subparsers = parser.add_subparsers(
        required=True,
        dest="_entrypoint",
        metavar=f'{{{", ".join(entrypoints.keys())}}}',
    )
    for cmd in entrypoints:
        _apply_argspec(
            subparsers.add_parser(cmd),
            entrypoints[cmd]._argspec,  # type: ignore # pylint: disable=protected-access
        )

    args = parser.parse_args()

    entrypoint = entrypoints[args._entrypoint]  # pylint: disable=protected-access
    del args._entrypoint
    entrypoint(**vars(args))


def _get_all_functions(
    package: ModuleType,
) -> Generator[tuple[str, FunctionType], None, None]:
    for _, name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        if name.startswith("orison.template"):
            continue
        module = importlib.import_module(name)
        for name, func in inspect.getmembers(module, inspect.isfunction):
            yield name, func


def _is_entrypoint(name: str, function: Any) -> bool:
    if not callable(function):
        return False
    if name.startswith("_"):
        return False
    return hasattr(function, "_argspec")


def _apply_argspec(parser: ArgumentParser, argspec: dict[str, Arg]) -> None:
    for name, spec in argspec.items():
        if spec._type == "positional":  # pylint: disable=protected-access
            arg = [name]
        elif spec.short is not None:
            arg = [f"-{spec.short}", f"--{name}"]
        else:
            arg = [f"--{name}"]
        action = (
            "store_true"
            if spec._type == "switch"  # pylint: disable=protected-access
            else "store"
        )
        parser.add_argument(
            *arg,
            action=action,
            help=spec.help,
        )
