"""Tests for plankarep.extensions."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from plankarep.filters import build_environment


def test_now_tag_uses_default_format(tmp_path: Path) -> None:
    environment = build_environment(tmp_path)

    rendered = environment.from_string("{% now %}").render()

    assert rendered == datetime.now(tz=UTC).strftime("%Y-%m-%d")


def test_now_tag_uses_explicit_format(tmp_path: Path) -> None:
    environment = build_environment(tmp_path)

    rendered = environment.from_string("{% now '%Y' %}").render()

    assert rendered == str(datetime.now(tz=UTC).year)
