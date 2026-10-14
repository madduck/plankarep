"""Shared test fixtures."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol

import pytest
from plankarep.config import Config, PlnkConfig


class CompletedFactory(Protocol):
    """Build a fake completed process for a test."""

    def __call__(
        self, *, stdout: str = ..., stderr: str = ..., returncode: int = ...
    ) -> subprocess.CompletedProcess[str]:
        """Build and return one fake completed process."""
        ...


class PayloadFactory(Protocol):
    """Build a successful ``plnk`` JSON payload."""

    def __call__(self, data: Any = ...) -> str:
        """Build and return one JSON payload string."""
        ...


class RunnerFactory(Protocol):
    """Build a recording fake runner."""

    def __call__(
        self,
        completed: subprocess.CompletedProcess[str] | None = ...,
        error: BaseException | None = ...,
    ) -> Any:
        """Build and return one fake runner."""
        ...


@pytest.fixture
def make_completed() -> Callable[..., subprocess.CompletedProcess[str]]:
    """Return a factory for fake completed processes."""

    def _make(
        *, stdout: str = "", stderr: str = "", returncode: int = 0
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["plnk"], returncode=returncode, stdout=stdout, stderr=stderr
        )

    return _make


@pytest.fixture
def make_payload() -> Callable[..., str]:
    """Return a factory for successful ``plnk`` JSON payloads."""

    def _make(data: Any = None) -> str:
        if data is None:
            data = [{"id": "1", "name": "Card"}]
        return json.dumps({"success": True, "data": data, "meta": {"count": len(data)}})

    return _make


@pytest.fixture
def config() -> Config:
    """Return a simple configuration with one view."""
    return Config(
        plnk=PlnkConfig(server="https://planka.example.org", token="tok"),  # nosec B106
        views={"cards": "card list --board 1"},
    )


class FakeRunner:
    """Callable runner that records invocations and returns a fixed result."""

    def __init__(
        self,
        completed: subprocess.CompletedProcess[str] | None = None,
        error: BaseException | None = None,
    ) -> None:
        """Store the result to return and the call log to fill.

        Args:
            completed: The process outcome to return.
            error: An exception to raise instead of returning.
        """
        self.completed = completed
        self.error = error
        self.calls: list[tuple[list[str], dict[str, str]]] = []

    def __call__(
        self, argv: Sequence[str], env: Mapping[str, str]
    ) -> subprocess.CompletedProcess[str]:
        """Record the invocation and return the stored result."""
        self.calls.append((list(argv), dict(env)))
        if self.error is not None:
            raise self.error
        assert self.completed is not None
        return self.completed


@pytest.fixture
def fake_runner() -> type[FakeRunner]:
    """Expose the :class:`FakeRunner` class to tests."""
    return FakeRunner


class StubRunner:
    """Runner that ignores its arguments and returns a stored process."""

    def __init__(self, completed: subprocess.CompletedProcess[str]) -> None:
        """Store the process to return.

        Args:
            completed: The process outcome to return for every call.
        """
        self.completed = completed

    def __call__(
        self, argv: Sequence[str], env: Mapping[str, str]
    ) -> subprocess.CompletedProcess[str]:
        """Return the stored process and ignore the invocation."""
        del argv, env
        return self.completed


@pytest.fixture
def stub_runner() -> type[StubRunner]:
    """Expose the :class:`StubRunner` class to tests."""
    return StubRunner
