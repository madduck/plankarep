#!/usr/bin/env python3
"""Read Markdown from stdin and post it to a Matrix room as formatted text."""

from __future__ import annotations

import asyncio
import sys
import time

import click
import markdown2
from nio import AsyncClient, RoomSendError

MAX_BYTES = 62_000  # Matrix events are limited to ~64 KB

_HOMESERVER_HELP = "Matrix homeserver URL; 'https://' is added when missing."
_ROOM_HELP = "Matrix room ID; a leading '!' is added when missing."
_CREDENTIALS_HELP = "Matrix access token used to authenticate with the homeserver."


def truncate_at_line(text: str, limit: int) -> str:
    """Trim text to at most `limit` bytes, cutting at a line boundary."""
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text
    cut = encoded[:limit].decode("utf-8", errors="ignore")
    newline = cut.rfind("\n")
    return cut[:newline] if newline != -1 else cut


def normalise_homeserver(homeserver: str) -> str:
    """Ensure `homeserver` carries an explicit ``https://`` scheme."""
    if "://" in homeserver:
        return homeserver.rstrip("/")
    return f"https://{homeserver}".rstrip("/")


def normalise_room_id(room_id: str) -> str:
    """Ensure `room_id` starts with the Matrix room sigil ``!``."""
    if room_id.startswith("!"):
        return room_id
    return f"!{room_id}"


def render_body(markdown_text: str) -> dict[str, str]:
    """Build the ``m.room.message`` content from Markdown text."""
    html = markdown2.markdown(
        markdown_text,
        extras=["fenced-code-blocks", "tables", "strike"],
    )
    return {
        "msgtype": "m.text",
        "body": markdown_text,  # Markdown fallback for plain clients
        "format": "org.matrix.custom.html",
        "formatted_body": html,  # what Element renders
    }


async def send(
    homeserver: str, room_id: str, token: str, content: dict[str, str]
) -> None:
    """Send `content` to `room_id` through a logged-in `matrix-nio` client."""
    client = AsyncClient(normalise_homeserver(homeserver))
    client.access_token = token
    try:
        response = await client.room_send(
            room_id=normalise_room_id(room_id),
            message_type="m.room.message",
            content=content,
            tx_id=str(time.time_ns()),
        )
    finally:
        await client.close()

    if isinstance(response, RoomSendError):
        msg = f"could not send message: {response.message}"
        raise click.ClickException(msg)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("-s", "--homeserver", required=True, help=_HOMESERVER_HELP)
@click.option("-r", "--room", "room_id", required=True, help=_ROOM_HELP)
@click.option("-t", "--token", required=True, help=_CREDENTIALS_HELP)
def main(homeserver: str, room_id: str, token: str) -> None:
    """Post Markdown read from standard input to a Matrix room."""
    markdown_text = sys.stdin.read()
    if not markdown_text.strip():
        return  # nothing to say

    markdown_text = truncate_at_line(markdown_text, MAX_BYTES)
    content = render_body(markdown_text)
    asyncio.run(send(homeserver, room_id, token, content))


if __name__ == "__main__":
    main()
