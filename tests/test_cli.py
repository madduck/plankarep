"""Tests for plankarep.cli."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from plankarep.cli import main

from tests.conftest import CompletedFactory

CONFIG = "[views]\nc = 'card list'\n"
PAYLOAD = json.dumps({"success": True, "data": [{"name": "Alpha"}]})


def write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    """Write a config and template file and return their paths."""
    config = tmp_path / "plankarep.toml"
    config.write_text(CONFIG, encoding="utf-8")
    template = tmp_path / "t.j2"
    template.write_text("{{ views.c[0].name }}", encoding="utf-8")
    return config, template


def patch_runner(
    monkeypatch: pytest.MonkeyPatch,
    completed: subprocess.CompletedProcess[str],
    stub_runner: Any,
) -> None:
    """Patch the default runner to return the given process."""
    monkeypatch.setattr("plankarep.engine.run_plnk", stub_runner(completed))


def test_cli_renders_template_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    make_completed: CompletedFactory,
    stub_runner: Any,
) -> None:
    config, template = write_inputs(tmp_path)
    patch_runner(monkeypatch, make_completed(stdout=PAYLOAD), stub_runner)

    result = CliRunner().invoke(
        main, ["--config", str(config), "--template", str(template)]
    )

    assert result.exit_code == 0
    assert result.output == "Alpha"


def test_cli_reads_template_from_stdin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    make_completed: CompletedFactory,
    stub_runner: Any,
) -> None:
    config, _ = write_inputs(tmp_path)
    patch_runner(monkeypatch, make_completed(stdout=PAYLOAD), stub_runner)

    result = CliRunner().invoke(
        main,
        ["--config", str(config), "--template", "-"],
        input="{{ views.c[0].name }}",
    )

    assert result.exit_code == 0
    assert result.output == "Alpha"


def test_cli_writes_output_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    make_completed: CompletedFactory,
    stub_runner: Any,
) -> None:
    config, template = write_inputs(tmp_path)
    patch_runner(monkeypatch, make_completed(stdout=PAYLOAD), stub_runner)
    output = tmp_path / "out.txt"

    result = CliRunner().invoke(
        main,
        ["--config", str(config), "--template", str(template), "--output", str(output)],
    )

    assert result.exit_code == 0
    assert output.read_text(encoding="utf-8") == "Alpha"


def test_cli_leaves_output_untouched_when_a_view_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    make_completed: CompletedFactory,
    stub_runner: Any,
) -> None:
    config, template = write_inputs(tmp_path)
    failure = json.dumps({"success": False, "data": []})
    patch_runner(monkeypatch, make_completed(stdout=failure), stub_runner)
    output = tmp_path / "out.txt"
    output.write_text("previous", encoding="utf-8")

    result = CliRunner().invoke(
        main,
        ["--config", str(config), "--template", str(template), "--output", str(output)],
    )

    assert result.exit_code == 1
    assert output.read_text(encoding="utf-8") == "previous"


def test_cli_reports_unwritable_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    make_completed: CompletedFactory,
    stub_runner: Any,
) -> None:
    config, template = write_inputs(tmp_path)
    patch_runner(monkeypatch, make_completed(stdout=PAYLOAD), stub_runner)

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config),
            "--template",
            str(template),
            "--output",
            str(tmp_path / "absent" / "out.txt"),
        ],
    )

    assert result.exit_code == 1
    assert "cannot write" in result.output


def test_cli_reports_view_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    make_completed: CompletedFactory,
    stub_runner: Any,
) -> None:
    config, template = write_inputs(tmp_path)
    failure = json.dumps({"success": False, "data": []})
    patch_runner(monkeypatch, make_completed(stdout=failure), stub_runner)

    result = CliRunner().invoke(
        main, ["--config", str(config), "--template", str(template)]
    )

    assert result.exit_code == 1
    assert "reported failure" in result.output


def test_cli_reports_missing_config(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        main, ["--config", str(tmp_path / "absent.toml"), "--template", "-"]
    )

    assert result.exit_code == 1
    assert "cannot read configuration" in result.output


def test_cli_reports_missing_template(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    make_completed: CompletedFactory,
    stub_runner: Any,
) -> None:
    config, _ = write_inputs(tmp_path)
    patch_runner(monkeypatch, make_completed(stdout=PAYLOAD), stub_runner)

    result = CliRunner().invoke(
        main, ["--config", str(config), "--template", str(tmp_path / "absent.j2")]
    )

    assert result.exit_code == 1
    assert "not found" in result.output
