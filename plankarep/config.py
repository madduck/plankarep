"""Configuration loading and validation.

The configuration lives in a TOML file with three sections: ``[plankarep]``
holds the rendering options, ``[plnk]`` holds the parameters that every
``plnk`` invocation shares, and ``[views]`` maps a view name to the ``plnk``
command line arguments that produce its data.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import PlankarepError

#: String keys accepted in the ``[plnk]`` section.
PLNK_STRING_KEYS = frozenset({"server", "token", "project", "board", "list"})

#: Boolean keys accepted in the ``[plnk]`` section.
PLNK_BOOL_KEYS = frozenset({"names"})

_PLNK_KEYS = PLNK_STRING_KEYS | PLNK_BOOL_KEYS


#: Boolean keys accepted in the ``[plankarep]`` section.
PLANKAREP_BOOL_KEYS = frozenset({"autoescape"})


@dataclass(frozen=True)
class RenderOptions:
    """Options that control template rendering.

    Attributes:
        autoescape: Whether Jinja2 escapes HTML-significant characters in
            template variables. The default is ``False``, because plankarep
            produces plain-text reports.
    """

    autoescape: bool = False


@dataclass(frozen=True)
class PlnkConfig:
    """Parameters shared by every ``plnk`` invocation.

    Attributes:
        server: Planka server URL, passed as ``--server``.
        token: Planka API token, passed as ``--token``.
        names: Whether to resolve names. ``True`` adds ``--names``, ``False``
            adds ``--no-names``, and ``None`` omits both.
        project: Default project name, exported as ``PLNK_PROJECT``.
        board: Default board name, exported as ``PLNK_BOARD``.
        list: Default list name, exported as ``PLNK_LIST``.
    """

    server: str | None = None
    token: str | None = None
    names: bool | None = None
    project: str | None = None
    board: str | None = None
    list: str | None = None  # mirrors the plnk option name


@dataclass(frozen=True)
class Config:
    """A parsed plankarep configuration.

    Attributes:
        render: Options that control template rendering.
        plnk: Parameters shared by every ``plnk`` invocation.
        views: Mapping of view name to the ``plnk`` command line arguments.
    """

    render: RenderOptions = field(default_factory=RenderOptions)
    plnk: PlnkConfig = field(default_factory=PlnkConfig)
    views: dict[str, str] = field(default_factory=dict)


def _parse_plnk(raw: Any) -> PlnkConfig:
    """Build a :class:`PlnkConfig` from the raw ``[plnk]`` table.

    Args:
        raw: The value of the ``[plnk]`` table, or an empty mapping.

    Returns:
        The validated configuration.

    Raises:
        PlankarepError: If the table or one of its values has the wrong type.
    """
    if not isinstance(raw, dict):
        msg = "[plnk] must be a table"
        raise PlankarepError(msg)

    unknown = set(raw) - _PLNK_KEYS
    if unknown:
        msg = f"[plnk] has unknown keys: {', '.join(sorted(unknown))}"
        raise PlankarepError(msg)

    values: dict[str, Any] = {}
    for key in PLNK_STRING_KEYS:
        value = raw.get(key)
        if value is not None:
            if not isinstance(value, str):
                msg = f"[plnk] key {key!r} must be a string"
                raise PlankarepError(msg)
            values[key] = value

    names = raw.get("names")
    if names is not None and not isinstance(names, bool):
        msg = "[plnk] key 'names' must be a boolean"
        raise PlankarepError(msg)
    values["names"] = names

    return PlnkConfig(**values)


def _parse_render(raw: Any) -> RenderOptions:
    """Build a :class:`RenderOptions` from the raw ``[plankarep]`` table.

    Args:
        raw: The value of the ``[plankarep]`` table, or an empty mapping.

    Returns:
        The validated rendering options.

    Raises:
        PlankarepError: If the table or one of its values has the wrong type.
    """
    if not isinstance(raw, dict):
        msg = "[plankarep] must be a table"
        raise PlankarepError(msg)

    unknown = set(raw) - PLANKAREP_BOOL_KEYS
    if unknown:
        msg = f"[plankarep] has unknown keys: {', '.join(sorted(unknown))}"
        raise PlankarepError(msg)

    autoescape = raw.get("autoescape", RenderOptions.autoescape)
    if not isinstance(autoescape, bool):
        msg = "[plankarep] key 'autoescape' must be a boolean"
        raise PlankarepError(msg)

    return RenderOptions(autoescape=autoescape)


def _parse_views(raw: Any) -> dict[str, str]:
    """Build the views mapping from the raw ``[views]`` table.

    Args:
        raw: The value of the ``[views]`` table.

    Returns:
        The validated view mapping.

    Raises:
        PlankarepError: If the table is missing or a command is not a string.
    """
    if raw is None:
        msg = "configuration is missing the [views] table"
        raise PlankarepError(msg)
    if not isinstance(raw, dict):
        msg = "[views] must be a table"
        raise PlankarepError(msg)

    views: dict[str, str] = {}
    for name, command in raw.items():
        if not isinstance(command, str):
            msg = f"[views] entry {name!r} must be a string"
            raise PlankarepError(msg)
        views[str(name)] = command
    return views


def load_config(path: Path) -> Config:
    """Load and validate a plankarep configuration file.

    Args:
        path: Path to the TOML configuration file.

    Returns:
        The parsed configuration.

    Raises:
        PlankarepError: If the file cannot be read, is not valid TOML, or does
            not match the expected schema.
    """
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        msg = f"cannot read configuration {path}: {exc}"
        raise PlankarepError(msg) from exc
    except tomllib.TOMLDecodeError as exc:
        msg = f"cannot parse configuration {path}: {exc}"
        raise PlankarepError(msg) from exc

    return Config(
        render=_parse_render(raw.get("plankarep", {})),
        plnk=_parse_plnk(raw.get("plnk", {})),
        views=_parse_views(raw.get("views")),
    )
