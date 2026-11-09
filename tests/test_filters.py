"""Tests for plankarep.filters."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from plankarep.filters import (
    build_environment,
    datefmt,
    is_future,
    is_past,
    sort_by_date,
)

NOW = datetime(2026, 10, 26, 13, 0, tzinfo=UTC)

CARDS = [
    {"name": "later", "dueDate": "2026-10-27T00:00:00Z"},
    {"name": "undated", "dueDate": None},
    {"name": "earlier", "dueDate": "2026-10-25T00:00:00Z"},
]


def test_datefmt_formats_zulu_timestamp() -> None:
    assert datefmt("2026-10-26T13:00:00.000Z", "%Y-%m-%d") == "2026-10-26"


def test_datefmt_uses_default_format_and_assumes_utc() -> None:
    assert datefmt("2026-10-26T13:00:00") == "2026-10-26"


def test_datefmt_renders_none_as_empty() -> None:
    assert datefmt(None) == ""


def test_datefmt_renders_missing_as_empty() -> None:
    environment = build_environment()

    rendered = environment.from_string("{{ card.dueDate | datefmt }}").render(card={})

    assert rendered == ""


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


def test_sort_by_date_orders_by_parsed_timestamp() -> None:
    environment = build_environment()

    assert [card["name"] for card in sort_by_date(environment, CARDS, "dueDate")] == [
        "earlier",
        "later",
        "undated",
    ]


def test_sort_by_date_reverses_dated_items_but_keeps_undated_last() -> None:
    environment = build_environment()

    assert [
        card["name"]
        for card in sort_by_date(environment, CARDS, "dueDate", reverse=True)
    ] == ["later", "earlier", "undated"]


def test_sort_by_date_treats_missing_timestamp_as_undated() -> None:
    environment = build_environment()
    cards = [
        {"name": "missing"},
        {"name": "dated", "dueDate": "2026-10-26T00:00:00Z"},
        {"name": "none", "dueDate": None},
    ]

    assert [card["name"] for card in sort_by_date(environment, cards, "dueDate")] == [
        "dated",
        "missing",
        "none",
    ]


def test_sort_by_date_keeps_undated_items_in_original_order() -> None:
    environment = build_environment()
    cards = [
        {"name": "undated-a", "dueDate": None},
        {"name": "dated", "dueDate": "2026-10-26T00:00:00Z"},
        {"name": "undated-b", "dueDate": None},
    ]

    assert [card["name"] for card in sort_by_date(environment, cards, "dueDate")] == [
        "dated",
        "undated-a",
        "undated-b",
    ]


def test_sort_by_date_supports_dotted_attributes() -> None:
    environment = build_environment()
    cards = [
        {"card": {"name": "later", "dueDate": "2026-10-27T00:00:00Z"}},
        {"card": {"name": "earlier", "dueDate": "2026-10-25T00:00:00Z"}},
    ]

    assert [
        card["card"]["name"]
        for card in sort_by_date(environment, cards, "card.dueDate")
    ] == ["earlier", "later"]


def test_sort_by_date_works_in_a_template() -> None:
    environment = build_environment()
    template = environment.from_string(
        "{{ cards | sort_by_date(attribute='dueDate')"
        " | map(attribute='name') | join(',') }}"
    )

    rendered = template.render(cards=CARDS)

    assert rendered == "earlier,later,undated"


def test_build_environment_binds_now_as_an_aware_utc_datetime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    environment = build_environment()

    assert environment.filters["datefmt"] is datefmt
    assert environment.filters["sort_by_date"] is sort_by_date
    assert environment.tests["past"] is is_past
    assert environment.tests["future"] is is_future
    assert environment.globals["now"].tzinfo is UTC  # type: ignore[attr-defined]


def test_build_environment_renders_now(tmp_path: Path) -> None:
    environment = build_environment(tmp_path)

    rendered = environment.from_string("{{ now | datefmt('%Y') }}").render()

    assert rendered == str(datetime.now(tz=UTC).year)


def test_build_environment_uses_search_path(tmp_path: Path) -> None:
    (tmp_path / "greeting.j2").write_text("hello {{ name }}", encoding="utf-8")

    rendered = build_environment(tmp_path).get_template("greeting.j2").render(name="x")

    assert rendered == "hello x"


def test_build_environment_does_not_autoescape_by_default() -> None:
    rendered = build_environment(Path()).from_string("{{ value }}").render(value="<b>")

    assert rendered == "<b>"


def test_build_environment_autoescapes_when_requested() -> None:
    environment = build_environment(Path(), autoescape=True)

    rendered = environment.from_string("{{ value }}").render(value="<b>")

    assert rendered == "&lt;b&gt;"
