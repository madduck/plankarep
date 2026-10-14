"""Jinja2 extensions provided by plankarep."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from jinja2 import nodes
from jinja2.ext import Extension

if TYPE_CHECKING:
    from jinja2.parser import Parser


class NowExtension(Extension):
    """Add the ``{% now %}`` tag.

    The tag renders the current UTC time. It accepts an optional format
    string, defaulting to the same ``%Y-%m-%d`` format as the ``datefmt``
    filter::

        {% now %}                  {# 2026-10-26 #}
        {% now '%d.%m.%Y %H:%M' %} {# 26.10.2026 13:00 #}
    """

    tags = {"now"}

    def parse(self, parser: Parser) -> nodes.Node:
        """Parse a ``{% now %}`` tag into a call to :meth:`_render`.

        Args:
            parser: The parser for the current template.

        Returns:
            The call node that renders the tag.
        """
        lineno = next(parser.stream).lineno
        format_arg = (
            parser.parse_expression()
            if parser.stream.current.type != "block_end"
            else nodes.Const(None)
        )
        call = self.call_method("_render", args=[format_arg], lineno=lineno)
        return nodes.Output([call], lineno=lineno).set_lineno(lineno)

    def _render(self, fmt: str | None = None) -> str:
        """Render the tag.

        Args:
            fmt: A :meth:`datetime.datetime.strftime` format string.
                Defaults to ``%Y-%m-%d``.

        Returns:
            The current UTC time formatted with ``fmt``.
        """
        return datetime.now(tz=UTC).strftime(fmt if fmt is not None else "%Y-%m-%d")
