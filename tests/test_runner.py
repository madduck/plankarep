"""Tests for plankarep.runner."""

from __future__ import annotations

import os
import sys

from plankarep.runner import run_plnk


def test_run_plnk_captures_stdout_and_stderr() -> None:
    script = "import sys; print('out'); print('err', file=sys.stderr)"

    completed = run_plnk([sys.executable, "-c", script], dict(os.environ))

    assert completed.returncode == 0
    assert completed.stdout.strip() == "out"
    assert completed.stderr.strip() == "err"
