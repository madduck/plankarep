"""Tests for plankarep.filters."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from plankarep.filters import build_environment, datefmt, is_future, is_past

NOW = datetime(2026, 10, 26, 13, 0, tzinfo=UTC)


def test_datefmt_formats_zulu_timestamp() -> None:
    assert datefmt("2026-10-26T13:00:00.000Z", "%Y-%m-%d") == "2026-10-26"


def test_datefmt_uses_default_format_and_assumes_utc() -> None:
    assert datefmt("2026-10-26T13:00:00") == "2026-10-26"


def test_datefmt_renders_none_as_empty() -> None:
    assert datefmt(None) == ""


def test_is_past_with_explicit_reference() -> None:
    assert is_past("2026-10-25T00:00:00Z", NOW) is True
    assert is_past("2026-10-27T00:00:00Z", NOW) is False


def test_is_past_defaults_to_now() -> None:
    assert is_past(datetime(2000, 1, 1, tzinfo=UTC).isoformat()) is True


def test_is_future_with_explicit_reference() -> None:
    assert is_future("2026-10-27T00:00:00Z", NOW) is True
    assert is_future("2026-10-25T00:00:00Z", NOW) is False


def test_is_future_defaults_to_now() -> None:
    assert is_future(datetime(2999, 1, 1, tzinfo=UTC).isoformat()) is True


def test_build_environment_defaults_to_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    environment = build_environment()

    assert environment.filters["datefmt"] is datefmt
    assert environment.tests["past"] is is_past
    assert environment.tests["future"] is is_future


def test_build_environment_uses_search_path(tmp_path: Path) -> None:
    (tmp_path / "greeting.j2").write_text("hello {{ name }}", encoding="utf-8")

    rendered = build_environment(tmp_path).get_template("greeting.j2").render(name="x")

    assert rendered == "hello x"


def test_build_environment_autoescapes() -> None:
    rendered = build_environment(Path()).from_string("{{ value }}").render(value="<b>")

    assert rendered == "&lt;b&gt;"
