"""Functional tests for `setup` API."""

import logging
import os
import pathlib
import typing as t

import pytest

from amox.env import LOG_FORMAT_ENV, LOG_LEVEL_ENV
from amox.logging_ import log
from amox.parsers import JsonParser, LogfmtParser, LogLineParser
from amox.types_ import LogFormat
from tests.functional import (
    ParsabilityScript,
    ParsabilityTests,
    ScriptResult,
    ScriptRunner,
)
from tests.functional.scripts import setup as parsability_script
from tests.functional.scripts import setup_deferred, setup_level_scope, setup_name_scope


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
    def test_name_scope(
        self,
        log_format: LogFormat,
        parser: LogLineParser,
        script_runner: ScriptRunner,
    ) -> None:
        """name=... sets log level to DEBUG."""
        filename = pathlib.Path(setup_name_scope.__file__).name
        env = {**os.environ, LOG_FORMAT_ENV: log_format}
        result: ScriptResult = script_runner(filename, env=env)

        assert result.returncode == 0

        expected = [
            (
                setup_name_scope.MSG,
                setup_name_scope.LEVEL,
                setup_name_scope.NAME,
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
            ("INFO", 1),
            ("WARNING", 0),
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
        """
        `LOG_LEVEL_ENV` with `setup()` controls third-party log visibility.

        Equivalent to `setup(level=...)`, setting as part of environment to
        parametrize at the test level.
        """
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
            assert parsed["msg"] == setup_level_scope.MSG
            assert parsed["logger"] == setup_level_scope.NAME
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
    def test_deferred_log_duplication(
        self,
        log_format: LogFormat,
        parser: LogLineParser,
        script_runner: ScriptRunner,
    ) -> None:
        """Call followed after existing managed loggers does not duplicate logs."""
        filename = pathlib.Path(setup_deferred.__file__).name
        env = {**os.environ, LOG_FORMAT_ENV: log_format}
        result: ScriptResult = script_runner(filename, env=env)

        assert result.returncode == 0

        msg_lines = [
            line
            for line in result.lines
            if parser.parse_line(line)["msg"] == setup_deferred.MSG
        ]
        assert len(msg_lines) == 1

    @pytest.mark.functional
    @pytest.mark.parametrize(
        ("log_format", "parser"),
        [
            ("logfmt", LogfmtParser()),
            ("json", JsonParser()),
        ],
        ids=["logfmt", "json"],
    )
    def test_deferred_logs_warning(
        self,
        log_format: LogFormat,
        parser: LogLineParser,
        script_runner: ScriptRunner,
    ) -> None:
        """Call followed after existing managed loggers produces a log warning."""
        filename = pathlib.Path(setup_deferred.__file__).name
        env = {**os.environ, LOG_FORMAT_ENV: log_format}
        result: ScriptResult = script_runner(filename, env=env)

        assert result.returncode == 0

        for line in result.lines:
            parsed = parser.parse_line(line)
            if parsed["logger"] == log.name:
                assert parsed["level"] == logging.getLevelName(logging.WARNING)
                break
        else:
            pytest.fail("no warning line found in output")
