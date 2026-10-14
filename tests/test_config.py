"""Tests for plankarep.config."""

from __future__ import annotations

from pathlib import Path

import pytest
from plankarep.config import Config, PlnkConfig, load_config
from plankarep.errors import PlankarepError


def write_config(tmp_path: Path, text: str) -> Path:
    """Write TOML text to a temporary configuration file."""
    path = tmp_path / "plankarep.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_load_full_config(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        """
[plnk]
server = "https://planka.example.org"
token = "secret"
names = true
project = "My Project"
board = "My Board"
list = "My List"

[views]
overdue = "card list --due-before today"
done = "card list --list done"
""",
    )

    config = load_config(path)

    assert config == Config(
        plnk=PlnkConfig(
            server="https://planka.example.org",
            token="secret",  # nosec B106 - not a real credential
            names=True,
            project="My Project",
            board="My Board",
            list="My List",
        ),
        views={
            "overdue": "card list --due-before today",
            "done": "card list --list done",
        },
    )


def test_load_config_defaults(tmp_path: Path) -> None:
    path = write_config(tmp_path, '[views]\nall = "card list"\n')

    config = load_config(path)

    assert config == Config(plnk=PlnkConfig(), views={"all": "card list"})


def test_load_config_names_false(tmp_path: Path) -> None:
    path = write_config(
        tmp_path, "[plnk]\nnames = false\n\n[views]\nall = 'card list'\n"
    )

    assert load_config(path).plnk.names is False


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(PlankarepError, match="cannot read configuration"):
        load_config(tmp_path / "absent.toml")


def test_invalid_toml(tmp_path: Path) -> None:
    path = write_config(tmp_path, "this is not toml\n")

    with pytest.raises(PlankarepError, match="cannot parse configuration"):
        load_config(path)


def test_plnk_not_a_table(tmp_path: Path) -> None:
    path = write_config(tmp_path, 'plnk = "oops"\n\n[views]\nall = "card list"\n')

    with pytest.raises(PlankarepError, match=r"\[plnk\] must be a table"):
        load_config(path)


def test_plnk_unknown_key(tmp_path: Path) -> None:
    path = write_config(tmp_path, '[plnk]\nnope = true\n\n[views]\nall = "card list"\n')

    with pytest.raises(PlankarepError, match="unknown keys: nope"):
        load_config(path)


def test_plnk_string_key_wrong_type(tmp_path: Path) -> None:
    path = write_config(tmp_path, "[plnk]\nserver = 1\n\n[views]\nall = 'card list'\n")

    with pytest.raises(PlankarepError, match="key 'server' must be a string"):
        load_config(path)


def test_plnk_names_wrong_type(tmp_path: Path) -> None:
    path = write_config(
        tmp_path, "[plnk]\nnames = 'yes'\n\n[views]\nall = 'card list'\n"
    )

    with pytest.raises(PlankarepError, match="key 'names' must be a boolean"):
        load_config(path)


def test_views_missing(tmp_path: Path) -> None:
    path = write_config(tmp_path, "[plnk]\nserver = 'x'\n")

    with pytest.raises(PlankarepError, match="missing the \\[views\\] table"):
        load_config(path)


def test_views_not_a_table(tmp_path: Path) -> None:
    path = write_config(tmp_path, 'views = "oops"\n')

    with pytest.raises(PlankarepError, match=r"\[views\] must be a table"):
        load_config(path)


def test_view_command_wrong_type(tmp_path: Path) -> None:
    path = write_config(tmp_path, "[views]\nall = 1\n")

    with pytest.raises(PlankarepError, match="entry 'all' must be a string"):
        load_config(path)
