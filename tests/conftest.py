"""Shared fixtures."""

import logging
import sys
import types

import pytest

from amox.parsers import JsonParser, LogfmtParser, LogLineParser
from amox.types_ import LogFormat

ExcInfo = tuple[type[BaseException], BaseException, types.TracebackType]


def make_exc_info(exc: BaseException) -> ExcInfo:
    """Raise and capture: populate traceback of an exception."""
    try:
        raise exc
    except type(exc):
        info = sys.exc_info()
        assert info
        exc_type, maybe_exc, traceback = info
        assert exc_type
        assert maybe_exc
        assert traceback
        return (exc_type, maybe_exc, traceback)


def make_record(
    msg: str = "message",
    level: int = logging.INFO,
    name: str = "test",
    exc_info: tuple[type[BaseException], BaseException, types.TracebackType | None]
    | tuple[None, None, None]
    | None = None,
    **extras: object,
) -> logging.LogRecord:
    """Create `logging.LogRecord` instances with sensible defaults."""
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname="test.py",
        lineno=1,
        msg=msg,
        args=(),
        exc_info=exc_info,
    )
    # equivalent of `logging.<level>(extras={})`. since not available at the LogRecord's
    # __init__
    for k, v in extras.items():
        setattr(record, k, v)
    return record


@pytest.fixture
def record() -> logging.LogRecord:
    """Record instance with defaults."""
    return make_record()


@pytest.fixture(
    scope="session",
    params=["logfmt", "json"],
    ids=["logfmt", "json"],
)
def log_format(request: pytest.FixtureRequest) -> LogFormat:
    """Log format literal for factories."""
    return request.param


@pytest.fixture(scope="session")
def parser(log_format: LogFormat) -> LogLineParser:
    """Parser matching `LogFormat`s."""
    if log_format == "logfmt":
        return LogfmtParser()
    return JsonParser()
