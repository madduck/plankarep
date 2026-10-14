"""Instantiate Jinja2 templates from Planka data obtained via ``plnk``.

The package exposes a small public API:

* :class:`~plankarep.config.Config` and :func:`~plankarep.config.load_config`
  read the TOML configuration.
* :func:`~plankarep.engine.render` and
  :func:`~plankarep.engine.render_string` run every configured view and
  instantiate a template with the collected data.
* :class:`~plankarep.errors.PlankarepError` is raised for all expected
  failures.

The ``VERSION`` constant defaults to ``"unknown"`` until a build writes
``_version.py``.
"""

from .config import Config, PlnkConfig, load_config
from .engine import render, render_string
from .errors import PlankarepError

try:
    from ._version import __version__ as VERSION  # noqa: N812
except ModuleNotFoundError:  # pragma: no cover - _version.py is generated on build
    VERSION = "unknown"

__all__ = [
    "VERSION",
    "Config",
    "PlankarepError",
    "PlnkConfig",
    "load_config",
    "render",
    "render_string",
]
