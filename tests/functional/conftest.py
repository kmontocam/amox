"""Fixtures for functional (subprocess-based) tests."""

import logging
import os
import pathlib
import subprocess
import sys
import typing as t

import pytest

from amox.env import LOG_FORMAT_ENV, LOG_LEVEL_ENV
from amox.parsers import JsonParser, LogfmtParser, LogLineParser
from amox.types_ import LogFormat

SCRIPTS = pathlib.Path(__file__).parent / "scripts"


class ParsabilityScript(t.Protocol):
    """
    Contract for functional test script modules.

    Each script must export `MSG`, `NAME`, `LEVEL`, and `__file__`.
    """

    __file__: str
    MSG: str
    NAME: str
    LEVEL: int


class ScriptRunner(t.Protocol):
    """Protocol for `run_script` fixture."""

    def __call__(
        self,
        name: str,
        *,
        env: dict[str, str] | None = None,
    ) -> "ScriptResult":
        """Callable protocol for `run_script()`."""
        ...


class ScriptResult:
    """Result of running a script in a subprocess."""

    def __init__(
        self,
        completed_process: subprocess.CompletedProcess[str],
    ) -> None:
        """`subprocess.CompletedProcess[str]` sanitized outputs."""
        self.returncode: int = completed_process.returncode
        self.stdout: str = completed_process.stdout.strip()
        self.stderr: str = completed_process.stderr.strip()

    @property
    def lines(self) -> list[str]:
        """Output lines from `stderr`: stream with logger's handler destination."""
        return [line for line in self.stderr.splitlines() if line]


class ParsabilityTests:
    """
    Shared functional tests for structured log output.

    Not collected directly by pytest (no `Test` prefix). Subclasses provide
    a `parsability_script` fixture for the specific entry point under test.
    """

    @pytest.fixture
    def parsability_script(self) -> ParsabilityScript:
        """Script (module) that produces logs."""
        raise NotImplementedError

    @pytest.mark.functional
    @pytest.mark.parametrize(
        ("log_format", "parser"),
        [
            ("logfmt", LogfmtParser()),
            ("json", JsonParser()),
        ],
        ids=["logfmt", "json"],
    )
    def test_parsability(
        self,
        parsability_script: ParsabilityScript,
        log_format: LogFormat,
        parser: LogLineParser,
        script_runner: ScriptRunner,
    ) -> None:
        """Script produces a single parseable log line with expected fields."""
        filename = pathlib.Path(parsability_script.__file__).name
        env = {**os.environ, LOG_FORMAT_ENV: log_format, LOG_LEVEL_ENV: "INFO"}
        result: ScriptResult = script_runner(filename, env=env)

        assert result.returncode == 0
        assert len(result.lines) == 1

        (line,) = result.lines
        parsed = parser.parse_line(line)

        assert parsed["msg"] == parsability_script.MSG
        assert parsed["level"] == logging.getLevelName(parsability_script.LEVEL)
        assert parsed["logger"] == parsability_script.NAME
        assert parsed["ts"] is not None


@pytest.fixture
def script_runner() -> ScriptRunner:
    """Subprocess runner for standalone script files."""

    def runner(name: str, *, env: dict[str, str] | None = None) -> ScriptResult:
        script = SCRIPTS / name
        completed = subprocess.run(  # noqa: S603
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            env=env,
            timeout=8,
            check=True,
        )
        return ScriptResult(completed)

    return runner
