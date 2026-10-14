"""Subprocess runner used to invoke ``plnk``."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping, Sequence

#: A callable that runs ``plnk`` and returns the completed process.
#:
#: It receives the full argument vector and the complete environment to use.
Runner = Callable[[Sequence[str], Mapping[str, str]], subprocess.CompletedProcess[str]]


def run_plnk(
    argv: Sequence[str], env: Mapping[str, str]
) -> subprocess.CompletedProcess[str]:
    """Run ``plnk`` and capture its output.

    Args:
        argv: The complete argument vector, including ``plnk`` itself.
        env: The complete environment for the child process.

    Returns:
        The completed process with captured, text-mode output.
    """
    # The argument vector is built by plankarep; no shell is involved.
    return subprocess.run(  # nosec B603
        list(argv),
        capture_output=True,
        text=True,
        env=dict(env),
        check=False,
    )
