"""Amox."""

from amox.logging_ import config, get_logger, setup
from amox.types_ import FormatterOptions
from amox.warnings_ import AmoxConfigWarning, AmoxFormatWarning

__all__ = [
    "AmoxConfigWarning",
    "AmoxFormatWarning",
    "FormatterOptions",
    "config",
    "get_logger",
    "setup",
]

__version__ = "0.0.13"
