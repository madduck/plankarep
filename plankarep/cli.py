"""Command line interface for plankarep."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import IO

import click

from . import VERSION
from .config import load_config
from .engine import render, render_string
from .errors import PlankarepError

_CONFIG_HELP = "Path to the TOML configuration file."
_TEMPLATE_HELP = "Template to instantiate, or '-' to read it from standard input."
_OUTPUT_HELP = "Write the result here instead of standard output."


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=VERSION, prog_name="plankarep")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("plankarep.toml"),
    show_default=True,
    help=_CONFIG_HELP,
)
@click.option(
    "--template",
    "template",
    default="plankarep.j2",
    show_default=True,
    help=_TEMPLATE_HELP,
)
@click.option(
    "--output",
    "output",
    type=click.File("w", encoding="utf-8", lazy=True),
    default="-",
    show_default=True,
    help=_OUTPUT_HELP,
)
def main(config_path: Path, template: str, output: IO[str] | None) -> None:
    """Instantiate a template from data gathered by ``plnk``."""
    try:
        config = load_config(config_path)
        if template == "-":
            rendered = render_string(config, sys.stdin.read())
        else:
            template_path = Path(template)
            rendered = render(
                config, template_path.name, search_path=template_path.parent
            )
    except PlankarepError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(rendered, file=output, nl=False)


if __name__ == "__main__":  # pragma: no cover - module entry point
    main()
