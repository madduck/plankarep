"""Build hooks: generate the man page from ``plankarep.pod``."""

from __future__ import annotations

import subprocess
from pathlib import Path

from setuptools import setup

HERE = Path(__file__).resolve().parent
POD = HERE / "plankarep.pod"
MAN = HERE / "plankarep.1"


def build_manpage() -> str:
    """Render ``plankarep.1`` from ``plankarep.pod`` with ``pod2man``.

    Returns:
        The man page path relative to the project directory, as setuptools
        requires relative paths in build metadata.

    Raises:
        RuntimeError: If ``pod2man`` is not available.
    """
    try:
        subprocess.run(  # noqa: S603, S607 - fixed, trusted arguments
            [
                "pod2man",
                "--section=1",
                "--center=plankarep",
                "--release=plankarep",
                str(POD),
                str(MAN),
            ],
            check=True,
        )  # nosec B603 B607 - pod2man is trusted and resolved via PATH
    except FileNotFoundError as exc:
        msg = "pod2man is required to build plankarep"
        raise RuntimeError(msg) from exc
    return MAN.name


setup(data_files=[("share/man/man1", [build_manpage()])])
