"""Integration tests for uvicorn with amox's logging configuration."""

import os
import subprocess
import sys
import urllib.request

import pytest
from uvicorn.config import LOGGING_CONFIG

from amox.env import LOG_FORMAT_ENV, LOG_LEVEL_ENV
from amox.parsers import LogLineParser
from amox.types_ import LogFormat
from tests.integration.scripts import uvicorn_access, uvicorn_cli, uvicorn_log_config

UVICORN_LOGGERS: dict[str, object] = LOGGING_CONFIG["loggers"]

STARTUP_LINES = 3
SHUTDOWN_LINES = 3
FULL_LIFECYCLE_LINES = STARTUP_LINES + SHUTDOWN_LINES
"""
Uvicorn lifecycle log lines emitted by `uvicorn.error` logger.

Full cycle (lifespan=on, graceful shutdown):

    | Phase    | Message                           | Source            |
    | -------- | --------------------------------- | ----------------- |
    | startup  | Started server process [%d]       | server.py:90      |
    | startup  | Waiting for application startup.  | lifespan/on.py:48 |
    | startup  | Application startup complete.     | lifespan/on.py:62 |
    | shutdown | Waiting for application shutdown. | lifespan/on.py:67 |
    | shutdown | Application shutdown complete.    | lifespan/on.py:76 |
    | shutdown | Finished server process [%d]      | server.py:100     |

Reference:
    `https://github.com/kludex/uvicorn/blob/0.47.0/uvicorn/server.py`
    `https://github.com/kludex/uvicorn/blob/0.47.0/uvicorn/lifespan/on.py`
"""

CLI_STARTUP_LINES = 2
"""
Minimum log lines before external termination (lifespan=off).

    | Phase   | Message                              | Source        |
    | ------- | ------------------------------------ | ------------  |
    | startup | Started server process [%d]          | server.py:90  |
    | startup | Uvicorn running on {addr} (Press...) | server.py:222 |

Reference:
    `https://github.com/kludex/uvicorn/blob/0.47.0/uvicorn/server.py`
"""


class TestUvicorn:
    """Tests for uvicorn producing structured output via `log_config=config()`."""

    pytestmark = pytest.mark.integration

    def test_log_config(
        self,
        log_format: LogFormat,
        parser: LogLineParser,
    ) -> None:
        """Uvicorn's lifecycle logs are parseable structured output."""
        env = {**os.environ, LOG_FORMAT_ENV: log_format, LOG_LEVEL_ENV: "INFO"}

        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", uvicorn_log_config.__name__],
            capture_output=True,
            text=True,
            env=env,
            timeout=8,
            check=True,
        )

        assert result.returncode == 0

        lines = [line for line in result.stderr.splitlines() if line]
        assert len(lines) >= FULL_LIFECYCLE_LINES

        for line in lines:
            parsed = parser.parse_line(line)
            assert parsed["ts"] is not None
            assert parsed["level"] == "INFO"
            assert parsed["logger"] in UVICORN_LOGGERS

    def test_cli(
        self,
        log_format: LogFormat,
        parser: LogLineParser,
    ) -> None:
        """Uvicorn started via `--log-config` CLI flag produces structured output."""
        env = {**os.environ, LOG_FORMAT_ENV: log_format, LOG_LEVEL_ENV: "INFO"}

        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", uvicorn_cli.__name__],
            capture_output=True,
            text=True,
            env=env,
            timeout=8,
            check=True,
        )

        lines = [line for line in result.stderr.splitlines() if line]
        assert len(lines) >= CLI_STARTUP_LINES

        for line in lines:
            parsed = parser.parse_line(line)
            assert parsed["ts"] is not None
            assert parsed["level"] == "INFO"
            assert parsed["logger"] in UVICORN_LOGGERS

    def test_access(
        self,
        log_format: LogFormat,
        parser: LogLineParser,
    ) -> None:
        """Uvicorn's access log for an HTTP request is parseable structured output."""
        env = {**os.environ, LOG_FORMAT_ENV: log_format, LOG_LEVEL_ENV: "INFO"}

        with subprocess.Popen(  # noqa: S603
            [sys.executable, "-m", uvicorn_access.__name__],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            env=env,
        ) as proc:
            assert proc.stdout is not None
            ready_line = proc.stdout.readline().strip()
            # convention emitting ready signal with port after gracefully starting
            signal, port = ready_line.split()
            assert signal == uvicorn_access.READY_SIGNAL

            url = f"http://{uvicorn_access.HOST}:{port}/"
            urllib.request.urlopen(url, timeout=2)  # noqa: S310

            # server should self-terminate after serving one request
            _, stderr = proc.communicate(timeout=4)

        assert proc.returncode == 0

        lines = [line for line in stderr.splitlines() if line]
        access_lines: list[dict[str, object]] = []

        for line in lines:
            parsed = parser.parse_line(line)
            assert parsed["ts"] is not None
            assert parsed["level"] == "INFO"
            assert parsed["logger"] in UVICORN_LOGGERS
            # uvicorn.access goes to stdout in default config, but amox's
            # config routes all loggers to stderr via root handler propagation.
            if parsed["logger"] == "uvicorn.access":
                access_lines.append(parsed)

        assert len(access_lines) == 1

        (access_line,) = access_lines
        assert f"{uvicorn_access.HTTP_STATUS_RESPONSE_CODE}" in f"{access_line['msg']}"
