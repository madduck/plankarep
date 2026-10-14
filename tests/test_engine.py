"""Tests for plankarep.engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from plankarep.config import Config, PlnkConfig, RenderOptions
from plankarep.engine import (
    build_argv,
    build_env,
    collect_views,
    invoke_view,
    render,
    render_string,
)
from plankarep.errors import PlankarepError

from tests.conftest import CompletedFactory, PayloadFactory, RunnerFactory


def test_build_argv_defaults() -> None:
    assert build_argv("card list", PlnkConfig()) == [
        "plnk",
        "--output",
        "json",
        "card",
        "list",
    ]


def test_build_argv_includes_shared_options() -> None:
    plnk = PlnkConfig(server="https://s", token="t", names=True)  # nosec B106

    assert build_argv("card list", plnk) == [
        "plnk",
        "--output",
        "json",
        "--server",
        "https://s",
        "--token",
        "t",
        "--names",
        "card",
        "list",
    ]


def test_build_argv_no_names() -> None:
    assert build_argv("card list", PlnkConfig(names=False)) == [
        "plnk",
        "--output",
        "json",
        "--no-names",
        "card",
        "list",
    ]


def test_build_argv_rejects_unbalanced_quotes() -> None:
    with pytest.raises(PlankarepError, match="cannot parse view command"):
        build_argv('card "list', PlnkConfig())


def test_build_env_sets_plnk_variables() -> None:
    env = build_env(PlnkConfig(project="P", board="B", list="L"))

    assert env["PLNK_PROJECT"] == "P"
    assert env["PLNK_BOARD"] == "B"
    assert env["PLNK_LIST"] == "L"


def test_build_env_omits_unset_variables() -> None:
    env = build_env(PlnkConfig())

    assert "PLNK_PROJECT" not in env
    assert "PLNK_BOARD" not in env
    assert "PLNK_LIST" not in env


def test_invoke_view_returns_data(
    make_completed: CompletedFactory,
    make_payload: PayloadFactory,
    fake_runner: RunnerFactory,
) -> None:
    runner = fake_runner(make_completed(stdout=make_payload([{"id": "1"}])))

    result = invoke_view("v", "card list", PlnkConfig(project="P"), runner)

    assert result == [{"id": "1"}]
    argv, env = runner.calls[0]
    assert argv == ["plnk", "--output", "json", "card", "list"]
    assert env["PLNK_PROJECT"] == "P"


def test_invoke_view_reports_oserror(fake_runner: RunnerFactory) -> None:
    runner = fake_runner(error=OSError("boom"))

    with pytest.raises(PlankarepError, match="cannot run plnk: boom"):
        invoke_view("v", "card list", PlnkConfig(), runner)


def test_invoke_view_reports_nonzero_with_stderr(
    make_completed: CompletedFactory, fake_runner: RunnerFactory
) -> None:
    runner = fake_runner(make_completed(stderr="bad things", returncode=2))

    with pytest.raises(PlankarepError, match="exited with 2: bad things"):
        invoke_view("v", "card list", PlnkConfig(), runner)


def test_invoke_view_reports_nonzero_without_stderr(
    make_completed: CompletedFactory, fake_runner: RunnerFactory
) -> None:
    runner = fake_runner(make_completed(returncode=3))

    with pytest.raises(PlankarepError, match="exited with 3$"):
        invoke_view("v", "card list", PlnkConfig(), runner)


def test_invoke_view_rejects_invalid_json(
    make_completed: CompletedFactory, fake_runner: RunnerFactory
) -> None:
    runner = fake_runner(make_completed(stdout="not json"))

    with pytest.raises(PlankarepError, match="produced invalid JSON"):
        invoke_view("v", "card list", PlnkConfig(), runner)


def test_invoke_view_rejects_non_mapping_payload(
    make_completed: CompletedFactory, fake_runner: RunnerFactory
) -> None:
    runner = fake_runner(make_completed(stdout="[]"))

    with pytest.raises(PlankarepError, match="reported failure"):
        invoke_view("v", "card list", PlnkConfig(), runner)


def test_invoke_view_rejects_unsuccessful_payload(
    make_completed: CompletedFactory, fake_runner: RunnerFactory
) -> None:
    payload = json.dumps({"success": False, "data": []})
    runner = fake_runner(make_completed(stdout=payload))

    with pytest.raises(PlankarepError, match="success=False"):
        invoke_view("v", "card list", PlnkConfig(), runner)


def test_invoke_view_rejects_missing_data(
    make_completed: CompletedFactory, fake_runner: RunnerFactory
) -> None:
    runner = fake_runner(make_completed(stdout=json.dumps({"success": True})))

    with pytest.raises(PlankarepError, match="has no 'data' key"):
        invoke_view("v", "card list", PlnkConfig(), runner)


def test_collect_views_runs_every_view(
    make_completed: CompletedFactory,
    make_payload: PayloadFactory,
    fake_runner: RunnerFactory,
) -> None:
    runner = fake_runner(make_completed(stdout=make_payload([{"id": "1"}])))
    config = Config(plnk=PlnkConfig(), views={"a": "card list", "b": "card list"})

    result = collect_views(config, runner)

    assert result == {"a": [{"id": "1"}], "b": [{"id": "1"}]}
    assert len(runner.calls) == len(config.views)


def test_render_file(
    tmp_path: Path,
    make_completed: CompletedFactory,
    make_payload: PayloadFactory,
    fake_runner: RunnerFactory,
) -> None:
    (tmp_path / "t.j2").write_text(
        "{% for c in cards %}{{ c.name }}{% endfor %}", encoding="utf-8"
    )
    runner = fake_runner(make_completed(stdout=make_payload([{"name": "Alpha"}])))
    config = Config(plnk=PlnkConfig(), views={"cards": "card list"})

    assert render(config, "t.j2", search_path=tmp_path, runner=runner) == "Alpha"


def test_render_missing_template(
    tmp_path: Path, fake_runner: RunnerFactory, make_completed: CompletedFactory
) -> None:
    config = Config(plnk=PlnkConfig(), views={})
    runner = fake_runner(make_completed())

    with pytest.raises(PlankarepError, match="not found"):
        render(config, "absent.j2", search_path=tmp_path, runner=runner)


def test_render_honours_autoescape(
    tmp_path: Path,
    make_completed: CompletedFactory,
    make_payload: PayloadFactory,
    fake_runner: RunnerFactory,
) -> None:
    (tmp_path / "t.j2").write_text("{{ cards[0].name }}", encoding="utf-8")
    runner = fake_runner(make_completed(stdout=make_payload([{"name": "A & B"}])))
    config = Config(
        plnk=PlnkConfig(),
        render=RenderOptions(autoescape=True),
        views={"cards": "card list"},
    )

    assert render(config, "t.j2", search_path=tmp_path, runner=runner) == "A &amp; B"


def test_render_string_honours_autoescape(
    tmp_path: Path,
    make_completed: CompletedFactory,
    make_payload: PayloadFactory,
    fake_runner: RunnerFactory,
) -> None:
    runner = fake_runner(make_completed(stdout=make_payload([{"name": "A & B"}])))
    config = Config(
        plnk=PlnkConfig(),
        render=RenderOptions(autoescape=True),
        views={"cards": "card list"},
    )

    result = render_string(
        config, "{{ cards[0].name }}", search_path=tmp_path, runner=runner
    )

    assert result == "A &amp; B"


def test_render_reports_syntax_error(
    tmp_path: Path, fake_runner: RunnerFactory, make_completed: CompletedFactory
) -> None:
    (tmp_path / "bad.j2").write_text("{% for x in %}", encoding="utf-8")
    config = Config(plnk=PlnkConfig(), views={})
    runner = fake_runner(make_completed())

    with pytest.raises(PlankarepError, match="is invalid"):
        render(config, "bad.j2", search_path=tmp_path, runner=runner)


def test_render_reports_undefined_variable(
    tmp_path: Path, fake_runner: RunnerFactory, make_completed: CompletedFactory
) -> None:
    (tmp_path / "u.j2").write_text("{{ missing }}", encoding="utf-8")
    config = Config(plnk=PlnkConfig(), views={})
    runner = fake_runner(make_completed())

    with pytest.raises(PlankarepError, match="'missing' is undefined"):
        render(config, "u.j2", search_path=tmp_path, runner=runner)


def test_render_uses_default_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    make_completed: CompletedFactory,
    make_payload: PayloadFactory,
    stub_runner: Any,
) -> None:
    (tmp_path / "t.j2").write_text("{{ cards | length }}", encoding="utf-8")
    completed = make_completed(stdout=make_payload([{"id": "1"}, {"id": "2"}]))
    monkeypatch.setattr("plankarep.engine.run_plnk", stub_runner(completed))
    config = Config(plnk=PlnkConfig(), views={"cards": "card list"})

    assert render(config, "t.j2", search_path=tmp_path) == "2"


def test_render_string(
    tmp_path: Path,
    make_completed: CompletedFactory,
    make_payload: PayloadFactory,
    fake_runner: RunnerFactory,
) -> None:
    runner = fake_runner(make_completed(stdout=make_payload([{"name": "Alpha"}])))
    config = Config(plnk=PlnkConfig(), views={"cards": "card list"})

    result = render_string(
        config,
        "{% for c in cards %}{{ c.name }}{% endfor %}",
        search_path=tmp_path,
        runner=runner,
    )

    assert result == "Alpha"


def test_render_string_reports_syntax_error(
    tmp_path: Path, fake_runner: RunnerFactory, make_completed: CompletedFactory
) -> None:
    config = Config(plnk=PlnkConfig(), views={})
    runner = fake_runner(make_completed())

    with pytest.raises(PlankarepError, match="template is invalid"):
        render_string(config, "{% for x in %}", search_path=tmp_path, runner=runner)


def test_render_string_reports_undefined_variable(
    tmp_path: Path, fake_runner: RunnerFactory, make_completed: CompletedFactory
) -> None:
    config = Config(plnk=PlnkConfig(), views={})
    runner = fake_runner(make_completed())

    with pytest.raises(PlankarepError, match="template: 'missing' is undefined"):
        render_string(config, "{{ missing }}", search_path=tmp_path, runner=runner)
