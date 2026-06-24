"""Unit test configuration."""

import logging
import typing as t
from collections import abc

import pytest

from amox import FormatterOptions
from amox.types_ import LogFormat, LogLevel

type FilterCallable = abc.Callable[[logging.LogRecord], bool | logging.LogRecord]
"""
Filter as callable.
"""


class SupportsFilter(t.Protocol):
    """Protocol for filterer as a type."""

    def filter(self, record: logging.LogRecord, /) -> bool | logging.LogRecord:
        """Filter."""


class GetLoggerKwargs(FormatterOptions, total=False):
    """Keyword arguments for `get_logger()`."""

    level: LogLevel | int
    log_format: LogFormat | None
    handlers: list[logging.Handler]
    queue: bool


@pytest.fixture(autouse=True)
def isolate_root_logger() -> abc.Generator[None]:
    """
    Clear root logger handlers before each test and restore after.

    Prevents test pollution from `setup()` calls or leftover handlers.
    """
    saved = logging.root.handlers
    logging.root.handlers.clear()
    yield
    logging.root.handlers = saved
