"""Functional tests for `setup` API."""

import logging
import os
import pathlib
import typing as t

import pytest

from amox.env import LOG_FORMAT_ENV, LOG_LEVEL_ENV
from amox.parsers import JsonParser, LogfmtParser, LogLineParser
from amox.types_ import LogFormat
from tests.functional import (
    ParsabilityScript,
    ParsabilityTests,
    ScriptResult,
    ScriptRunner,
)
from tests.functional.scripts import setup as parsability_script
from tests.functional.scripts import (
    setup_after_get_logger,
    setup_level_scope,
    setup_name_scope,
)


class TestSetup(ParsabilityTests):
    """Tests for `setup()` API."""

    @t.override
    @pytest.fixture
    def parsability_script(self) -> ParsabilityScript:
        return parsability_script

    @pytest.mark.functional
    @pytest.mark.parametrize(
        ("log_format", "parser"),
        [
            ("logfmt", LogfmtParser()),
            ("json", JsonParser()),
        ],
        ids=["logfmt", "json"],
    )
    def test_name_scopes(
        self,
        log_format: LogFormat,
        parser: LogLineParser,
        script_runner: ScriptRunner,
    ) -> None:
        """`setup(name=...)` promotes app to DEBUG, third-party INFO visible."""
        filename = pathlib.Path(setup_name_scope.__file__).name
        env = {**os.environ, LOG_FORMAT_ENV: log_format, LOG_LEVEL_ENV: "INFO"}
        result: ScriptResult = script_runner(filename, env=env)

        assert result.returncode == 0

        expected = [
            (
                setup_name_scope.MSG,
                setup_name_scope.LEVEL,
                setup_name_scope.NAME,
            ),
            (
                setup_name_scope.THIRD_PARTY_MSG,
                setup_name_scope.THIRD_PARTY_LEVEL,
                setup_name_scope.THIRD_PARTY,
            ),
        ]

        assert len(result.lines) == len(expected)

        for line, (msg, level, logger) in zip(result.lines, expected, strict=True):
            parsed = parser.parse_line(line)
            assert parsed["msg"] == msg
            assert parsed["level"] == logging.getLevelName(level)
            assert parsed["logger"] == logger

    @pytest.mark.functional
    @pytest.mark.parametrize(
        ("log_format", "parser"),
        [
            ("logfmt", LogfmtParser()),
            ("json", JsonParser()),
        ],
        ids=["logfmt", "json"],
    )
    @pytest.mark.parametrize(
        ("level", "expected"),
        [
            ("INFO", 2),
            ("WARNING", 1),
        ],
        ids=["info", "warning"],
    )
    def test_level_scope(
        self,
        log_format: LogFormat,
        parser: LogLineParser,
        level: str,
        expected: int,
        script_runner: ScriptRunner,
    ) -> None:
        """`LOG_LEVEL_ENV` with `setup()` controls third-party logs visibility."""
        filename = pathlib.Path(setup_level_scope.__file__).name
        env = {
            **os.environ,
            LOG_FORMAT_ENV: log_format,
            LOG_LEVEL_ENV: level,
        }
        result: ScriptResult = script_runner(filename, env=env)

        assert result.returncode == 0
        assert len(result.lines) == expected

        for line in result.lines:
            parsed = parser.parse_line(line)
            assert parsed["msg"] in (
                setup_level_scope.MSG,
                setup_level_scope.THIRD_PARTY_MSG,
            )
            assert parsed["logger"] in (
                setup_level_scope.NAME,
                setup_level_scope.THIRD_PARTY,
            )
            assert parsed["ts"] is not None

    @pytest.mark.functional
    @pytest.mark.parametrize(
        ("log_format", "parser"),
        [
            ("logfmt", LogfmtParser()),
            ("json", JsonParser()),
        ],
        ids=["logfmt", "json"],
    )
    def test_removes_get_logger_handlers(
        self,
        log_format: LogFormat,
        parser: LogLineParser,
        script_runner: ScriptRunner,
    ) -> None:
        """`setup()` warns when removing `get_logger`-managed handlers."""
        filename = pathlib.Path(setup_after_get_logger.__file__).name
        env = {**os.environ, LOG_FORMAT_ENV: log_format}
        result: ScriptResult = script_runner(filename, env=env)

        assert result.returncode == 0

        for line in result.lines:
            parsed = parser.parse_line(line)
            if parsed.get("logger") == "amox":
                assert parsed["level"] == logging.getLevelName(logging.WARNING)
                assert setup_after_get_logger.LOGGER in f"{parsed['msg']}"
                break
        else:
            pytest.fail("no amox warning line found in output")
