"""Lumberjack."""

from lumberjack.formatters import JsonFormatter, LogfmtFormatter, create_formatter
from lumberjack.logging_ import config, get_logger, setup
from lumberjack.types_ import FormatterOptions

__all__ = [
    "FormatterOptions",
    "JsonFormatter",
    "LogfmtFormatter",
    "config",
    "create_formatter",
    "get_logger",
    "setup",
]

__version__ = "0.0.2"
