"""Amox."""

from amox.formatters import JsonFormatter, LogfmtFormatter, create_formatter
from amox.logging_ import config, get_logger, setup
from amox.types_ import FormatterOptions

__all__ = [
    "FormatterOptions",
    "JsonFormatter",
    "LogfmtFormatter",
    "config",
    "create_formatter",
    "get_logger",
    "setup",
]

__version__ = "0.0.4"
