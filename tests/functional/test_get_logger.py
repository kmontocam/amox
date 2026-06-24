"""Functional tests for `get_logger` API."""

import logging
import os
import pathlib
import typing as t

import pytest

from amox.env import FORMAT_ENV, ROOT_LEVEL_ENV
from amox.parsers import LogLineParser
from amox.types_ import LogFormat
from tests.functional import (
    ParsabilityScript,
    ParsabilityTests,
    ScriptResult,
    ScriptRunner,
)
from tests.functional.scripts import get_logger, get_logger_handlers


class TestGetLogger(ParsabilityTests):
    """Tests for `get_logger()` API."""

    @t.override
    @pytest.fixture
    def parsability_script(self) -> ParsabilityScript:
        return get_logger

    def test_handlers_parsability(
        self,
        log_format: LogFormat,
        parser: LogLineParser,
        script_runner: ScriptRunner,
    ) -> None:
        """Additional handler receives a formatted record on its stream."""
        filename = pathlib.Path(get_logger_handlers.__file__).name
        env = {**os.environ, FORMAT_ENV: log_format, ROOT_LEVEL_ENV: "INFO"}
        result: ScriptResult = script_runner(filename, env=env)

        assert result.returncode == 0
        # additional handler streams to `stdout`, apply criteria as
        # `self.test_parsability`
        lines = [line for line in result.stdout.splitlines() if line]
        assert len(lines) == 1

        (line,) = lines
        parsed = parser.parse_line(line)

        assert parsed["msg"] == get_logger_handlers.MSG
        assert parsed["level"] == logging.getLevelName(get_logger_handlers.LEVEL)
        assert parsed["logger"] == get_logger_handlers.NAME
        assert parsed["ts"] is not None
