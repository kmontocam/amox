"""Functional tests for `setup` API."""

import logging
import os
import pathlib
import typing as t

import pytest

from amox.formatters import LOG_FORMAT_ENV
from amox.parsers import JsonParser, LogfmtParser, LogLineParser
from amox.types_ import LogFormat
from tests.functional import (
    ParsabilityScript,
    ParsabilityTests,
    ScriptResult,
    ScriptRunner,
)
from tests.functional.scripts import setup as parsability_script
from tests.functional.scripts import setup_scope


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
        """`setup(name=...)` promotes app to DEBUG, third-party's level on INFO."""
        filename = pathlib.Path(setup_scope.__file__).name
        env = {**os.environ, LOG_FORMAT_ENV: log_format}
        result: ScriptResult = script_runner(filename, env=env)

        assert result.returncode == 0

        expected = [
            (
                setup_scope.MSG,
                setup_scope.LEVEL,
                setup_scope.NAME,
            ),
            (
                setup_scope.THIRD_PARTY_MSG,
                setup_scope.THIRD_PARTY_LEVEL,
                setup_scope.THIRD_PARTY,
            ),
        ]

        assert len(result.lines) == len(expected)

        for line, (msg, level, logger) in zip(result.lines, expected, strict=True):
            parsed = parser.parse_line(line)
            assert parsed["msg"] == msg
            assert parsed["level"] == logging.getLevelName(level)
            assert parsed["logger"] == logger
