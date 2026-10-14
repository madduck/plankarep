"""Invoke configured views and instantiate templates with their data."""

from __future__ import annotations

import json
import os
import shlex
from pathlib import Path
from typing import Any

from jinja2 import Template, TemplateError, TemplateNotFound

from .config import Config, PlnkConfig
from .errors import PlankarepError
from .filters import build_environment
from .runner import Runner, run_plnk

#: Mapping of :class:`~plankarep.config.PlnkConfig` fields to environment
#: variables understood by ``plnk``.
PLNK_ENV_VARS = {
    "project": "PLNK_PROJECT",
    "board": "PLNK_BOARD",
    "list": "PLNK_LIST",
}

#: The executable invoked for every view.
PLNK_EXECUTABLE = "plnk"


def build_argv(view_command: str, plnk: PlnkConfig) -> list[str]:
    """Build the ``plnk`` argument vector for a view.

    The shared options from ``[plnk]`` come first, followed by the arguments
    from the view definition. ``--output json`` is always injected.

    Args:
        view_command: The shell-like command line from the ``[views]`` table.
        plnk: The shared ``plnk`` parameters.

    Returns:
        The complete argument vector, starting with the executable.

    Raises:
        PlankarepError: If ``view_command`` cannot be split into arguments.
    """
    argv = [PLNK_EXECUTABLE, "--output", "json"]
    if plnk.server is not None:
        argv += ["--server", plnk.server]
    if plnk.token is not None:
        argv += ["--token", plnk.token]
    if plnk.names is True:
        argv.append("--names")
    elif plnk.names is False:
        argv.append("--no-names")

    try:
        argv.extend(shlex.split(view_command))
    except ValueError as exc:
        msg = f"cannot parse view command {view_command!r}: {exc}"
        raise PlankarepError(msg) from exc
    return argv


def build_env(plnk: PlnkConfig) -> dict[str, str]:
    """Build the child environment for a ``plnk`` invocation.

    The current environment is inherited, with the ``PLNK_*`` variables for
    project, board, and list overriding any existing values.

    Args:
        plnk: The shared ``plnk`` parameters.

    Returns:
        The complete environment for the child process.
    """
    env = dict(os.environ)
    for field_name, variable in PLNK_ENV_VARS.items():
        value = getattr(plnk, field_name)
        if value is not None:
            env[variable] = value
    return env


def invoke_view(view: str, command: str, plnk: PlnkConfig, runner: Runner) -> Any:
    """Run a single view and return its ``data`` array.

    Args:
        view: The view name, used in error messages.
        command: The shell-like command line from the configuration.
        plnk: The shared ``plnk`` parameters.
        runner: The callable that executes ``plnk``.

    Returns:
        The JSON ``data`` value produced by ``plnk``.

    Raises:
        PlankarepError: If ``plnk`` cannot be run, exits non-zero, produces
            invalid JSON, reports failure, or omits ``data``.
    """
    argv = build_argv(command, plnk)
    env = build_env(plnk)

    try:
        completed = runner(argv, env)
    except OSError as exc:
        msg = f"view {view!r}: cannot run {PLNK_EXECUTABLE}: {exc}"
        raise PlankarepError(msg) from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        msg = f"view {view!r}: {PLNK_EXECUTABLE} exited with {completed.returncode}"
        if stderr:
            msg = f"{msg}: {stderr}"
        raise PlankarepError(msg)

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        msg = f"view {view!r}: {PLNK_EXECUTABLE} produced invalid JSON: {exc}"
        raise PlankarepError(msg) from exc

    if not isinstance(payload, dict) or payload.get("success") is not True:
        success = payload.get("success") if isinstance(payload, dict) else payload
        msg = f"view {view!r}: {PLNK_EXECUTABLE} reported failure (success={success!r})"
        raise PlankarepError(msg)

    try:
        return payload["data"]
    except KeyError as exc:
        msg = f"view {view!r}: {PLNK_EXECUTABLE} response has no 'data' key"
        raise PlankarepError(msg) from exc


def collect_views(config: Config, runner: Runner) -> dict[str, Any]:
    """Run every configured view and collect its data.

    Args:
        config: The plankarep configuration.
        runner: The callable that executes ``plnk``.

    Returns:
        Mapping of view name to the view's JSON ``data``.

    Raises:
        PlankarepError: If any view fails.
    """
    return {
        name: invoke_view(name, command, config.plnk, runner)
        for name, command in config.views.items()
    }


def build_context(config: Config, runner: Runner) -> dict[str, Any]:
    """Build the template context for a configuration.

    Every view is scoped under the ``views`` name, so the view ``overdue`` is
    available as ``views.overdue``. The context also contains ``server`` when
    the configuration provides a Planka server URL.

    Args:
        config: The plankarep configuration.
        runner: The callable that executes ``plnk``.

    Returns:
        Mapping of context name to its value.

    Raises:
        PlankarepError: If any view fails.
    """
    context: dict[str, Any] = {"views": collect_views(config, runner)}
    if config.plnk.server is not None:
        context["server"] = config.plnk.server
    return context


def _render_context(
    config: Config, template: Template, runner: Runner, description: str
) -> str:
    """Collect view data and render ``template`` with it."""
    try:
        return template.render(build_context(config, runner))
    except TemplateError as exc:
        msg = f"{description}: {exc}"
        raise PlankarepError(msg) from exc


def render(
    config: Config,
    template_name: str,
    *,
    search_path: Path | None = None,
    runner: Runner | None = None,
) -> str:
    """Instantiate a template file with data from the configured views.

    Args:
        config: The plankarep configuration.
        template_name: Template name relative to ``search_path``.
        search_path: Directory to load the template from. Defaults to the
            current working directory.
        runner: The callable that executes ``plnk``. Defaults to
            :func:`~plankarep.runner.run_plnk`.

    Returns:
        The rendered template as a string.

    Raises:
        PlankarepError: If the template cannot be loaded or rendered, or if a
            view fails.
    """
    environment = build_environment(search_path, autoescape=config.render.autoescape)
    try:
        template = environment.get_template(template_name)
    except TemplateNotFound as exc:
        msg = f"template {template_name!r} not found"
        raise PlankarepError(msg) from exc
    except TemplateError as exc:
        msg = f"template {template_name!r} is invalid: {exc}"
        raise PlankarepError(msg) from exc

    return _render_context(
        config, template, runner or run_plnk, f"template {template_name!r}"
    )


def render_string(
    config: Config,
    source: str,
    *,
    search_path: Path | None = None,
    runner: Runner | None = None,
) -> str:
    """Instantiate a template provided as a string.

    The loader still uses ``search_path`` so that templates rendered from
    standard input can extend or include files on disk.

    Args:
        config: The plankarep configuration.
        source: The template source.
        search_path: Directory used by ``{% extends %}`` and ``{% include %}``.
            Defaults to the current working directory.
        runner: The callable that executes ``plnk``. Defaults to
            :func:`~plankarep.runner.run_plnk`.

    Returns:
        The rendered template as a string.

    Raises:
        PlankarepError: If the template is invalid or a view fails.
    """
    environment = build_environment(search_path, autoescape=config.render.autoescape)
    try:
        template = environment.from_string(source)
    except TemplateError as exc:
        msg = f"template is invalid: {exc}"
        raise PlankarepError(msg) from exc

    return _render_context(config, template, runner or run_plnk, "template")
