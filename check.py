# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "black>=26.3.1",
#     "isort>=8.0.1",
#     "mypy>=1.20.2",
#     "pylint>=4.0.5",
# ]
# ///

import sys
from pathlib import Path

import orison
from orison import command, sh, typez

SRC = Path(__file__).resolve().parent / "src"
MYPYPATH = {"MYPYPATH": str(SRC)}


def uv(*cmd: str | typez.PathLike, env: dict[str, str] | None = None) -> None:
    sh.run("uv", "run", *cmd, env=env)


def mypy(path: typez.PathLike) -> None:
    uv("mypy", "--strict", path)


def black(path: typez.PathLike) -> None:
    uv("black", path)


def isort(path: typez.PathLike) -> None:
    uv("isort", path)


def pylint(path: typez.PathLike) -> None:
    uv("pylint", "--disable", "C0114,C0115,C0116,E0611,W0621,W0622,W0719", path)


def main() -> None:
    try:
        uv("mypy", "--strict", __file__, env=MYPYPATH)
        black(__file__)
        isort(__file__)
        pylint(__file__)

        entrypoint = SRC / "__main__.py"
        uv("mypy", "--strict", entrypoint, env=MYPYPATH)
        black(entrypoint)
        isort(entrypoint)
        pylint(entrypoint)

        module = SRC / "orison"
        uv(
            "mypy",
            "--strict",
            "-p",
            "orison",
            env=MYPYPATH,
        )
        black(module)
        isort(module)
        pylint(module)

        command.check(orison)

        sys.exit(0)
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
