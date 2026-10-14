"""Jinja2 environment construction and custom filters and tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

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
        value: The timestamp to format. ``None`` renders as an empty string.
        fmt: A :meth:`datetime.datetime.strftime` format string.

    Returns:
        The formatted timestamp, or an empty string for ``None``.
    """
    if value is None:
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


def now() -> datetime:
    """Return the current time as an aware UTC datetime.

    Templates call this to obtain a reference point for comparisons against
    Planka timestamps, or to format it with :func:`datefmt`.

    Returns:
        The current time in UTC.
    """
    return datetime.now(tz=UTC)


def build_environment(
    search_path: Path | None = None, *, autoescape: bool = False
) -> Environment:
    """Create the Jinja2 environment used to render templates.

    The environment uses strict undefined handling and loads templates from
    ``search_path`` so that ``{% extends %}`` and ``{% include %}`` resolve
    relative to the template.

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
    environment.tests["past"] = is_past
    environment.tests["future"] = is_future
    environment.globals["now"] = now
    return environment
