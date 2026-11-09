"""Jinja2 environment construction and custom filters and tests."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    Undefined,
    pass_environment,
)
from jinja2.filters import make_attrgetter

from .extensions import NowExtension


def _parse_datetime(value: Any) -> datetime:
    """Parse an ISO 8601 string into an aware datetime.

    Args:
        value: A string such as ``"2026-10-26T13:00:00.000Z"``.

    Returns:
        The parsed datetime. Naive values are assumed to be in UTC.

    Raises:
        ValueError: If the value is not a valid ISO 8601 datetime.
    """
    text = str(value)
    if text.endswith(("Z", "z")):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def datefmt(value: Any, fmt: str = "%Y-%m-%d") -> str:
    """Format an ISO 8601 timestamp.

    Args:
        value: The timestamp to format. ``None`` or a missing value renders as
            an empty string.
        fmt: A :meth:`datetime.datetime.strftime` format string.

    Returns:
        The formatted timestamp, or an empty string for ``None`` or a missing
        value.
    """
    if value is None or isinstance(value, Undefined):
        return ""
    return _parse_datetime(value).strftime(fmt)


def is_past(value: Any, now: datetime | None = None) -> bool:
    """Test whether a timestamp lies before a reference point.

    Args:
        value: The timestamp to test.
        now: The reference point. Defaults to the current UTC time.

    Returns:
        ``True`` if ``value`` is earlier than the reference point.
    """
    reference = now if now is not None else datetime.now(tz=UTC)
    return _parse_datetime(value) < reference


def is_future(value: Any, now: datetime | None = None) -> bool:
    """Test whether a timestamp lies after a reference point.

    Args:
        value: The timestamp to test.
        now: The reference point. Defaults to the current UTC time.

    Returns:
        ``True`` if ``value`` is later than the reference point.
    """
    reference = now if now is not None else datetime.now(tz=UTC)
    return _parse_datetime(value) > reference


@pass_environment
def sort_by_date(
    environment: Environment,
    value: Iterable[Any],
    attribute: str,
    *,
    reverse: bool = False,
) -> list[Any]:
    """Sort items by an ISO 8601 timestamp attribute, keeping undated items last.

    Jinja2's built-in ``sort`` filter compares raw values. If an item's
    timestamp is ``None``, comparing it with a string raises ``TypeError``.
    This filter parses the timestamps first and compares the resulting
    datetimes. Items whose timestamp is ``None`` or missing are appended after
    the sorted items, in their original order.

    Args:
        environment: The Jinja2 environment. The decorator supplies it.
        value: The items to sort.
        attribute: The attribute or key that holds the timestamp. Dot notation
            is supported, for example ``"card.dueDate"``.
        reverse: Sort descending instead of ascending. Undated items stay last.

    Returns:
        A new list with the dated items sorted and the undated items last.
    """
    get_attribute = make_attrgetter(environment, attribute)
    dated: list[tuple[datetime, Any]] = []
    undated: list[Any] = []
    for item in value:
        timestamp = get_attribute(item)
        if timestamp is None or isinstance(timestamp, Undefined):
            undated.append(item)
        else:
            dated.append((_parse_datetime(timestamp), item))
    dated.sort(key=lambda pair: pair[0], reverse=reverse)
    return [item for _, item in dated] + undated


def build_environment(
    search_path: Path | None = None, *, autoescape: bool = False
) -> Environment:
    """Create the Jinja2 environment used to render templates.

    The environment uses strict undefined handling and loads templates from
    ``search_path`` so that ``{% extends %}`` and ``{% include %}`` resolve
    relative to the template.

    The environment binds ``now`` to the time of construction. Every render
    builds a fresh environment, so a report shows one consistent timestamp
    even when the template reads ``now`` more than once.

    Args:
        search_path: Directory to load templates from. Defaults to the current
            working directory.
        autoescape: Whether to escape HTML-significant characters in template
            variables. The default is ``False``.

    Returns:
        The configured environment.
    """
    root = search_path if search_path is not None else Path.cwd()
    environment = Environment(
        loader=FileSystemLoader(str(root)),
        undefined=StrictUndefined,
        # plankarep produces plain-text reports. Autoescaping is opt-in via
        # the [plankarep] table; escaping HTML would mangle report text.
        autoescape=autoescape,  # nosec B701
        keep_trailing_newline=True,
        extensions=[NowExtension],
    )
    environment.filters["datefmt"] = datefmt
    environment.filters["sort_by_date"] = sort_by_date
    environment.tests["past"] = is_past
    environment.tests["future"] = is_future
    environment.globals["now"] = datetime.now(tz=UTC)
    return environment
