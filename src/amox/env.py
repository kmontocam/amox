"""Environment variable conventions and resolution logic."""

import os
import warnings

from amox.types_ import LogFormat, LogLevel
from amox.warnings_ import AmoxConfigWarning

LOG_FORMAT_ENV = "AMOX_LOG_FORMAT"
"""
Convention environment variable name to configure log format.
"""

LOG_LEVEL_ENV = "AMOX_LOG_LEVEL"
"""
Convention environment variable name to configure the root logger level.
"""

LOG_FORMATS: set[LogFormat] = {"json", "logfmt"}
"""
Valid log format identifiers for `AMOX_LOG_FORMAT`.
"""

LOG_LEVELS: set[LogLevel] = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
    "NOTSET",
}
"""
Valid log level names for `AMOX_LOG_LEVEL`.
"""

DEFAULT_FORMAT: LogFormat = "logfmt"
"""
Fallback log format when `AMOX_LOG_FORMAT` is unset.
"""

DEFAULT_ROOT_LEVEL: LogLevel = "WARNING"
"""
Fallback log level when `AMOX_LOG_LEVEL` is unset.

Default matches Python's stdlib `logging` module where the root logger is created with
`WARNING` and the internal `lastResort` handler defaults to `WARNING`: this keeps
third-party noise silent while surfacing warnings, errors, and critical events. Python's
logging HOWTO regards this as *"the best default behavior"*.

Reference:
    — `https://docs.python.org/3/library/logging.html#logging.Logger.setLevel`
    - `https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library`
"""


def resolve_format() -> LogFormat:
    """
    Resolve log format from `AMOX_LOG_FORMAT`.

    When the environment variable is not set, falls back to `DEFAULT_FORMAT`.
    Invalid values trigger an `AmoxConfigWarning` and fall back to the default.
    """
    env = os.environ.get(LOG_FORMAT_ENV)
    if env is None:
        return DEFAULT_FORMAT
    if env in LOG_FORMATS:
        return env  # ty: ignore[invalid-return-type]

    warnings.warn(
        (
            f"{LOG_FORMAT_ENV}={env!r} is not valid."
            f" Expected one of: {', '.join(LOG_FORMATS)}."
            f" Falling back to {DEFAULT_FORMAT!r}."
        ),
        AmoxConfigWarning,
        stacklevel=2,
    )
    return DEFAULT_FORMAT


def resolve_level() -> LogLevel:
    """
    Resolve root logger level from `AMOX_LOG_LEVEL`.

    When the environment variable is not set, falls back to `DEFAULT_ROOT_LEVEL`.
    Invalid values trigger an `AmoxConfigWarning` and fall back to the default.
    """
    env = os.environ.get(LOG_LEVEL_ENV)
    if env is None:
        return DEFAULT_ROOT_LEVEL
    if env in LOG_LEVELS:
        return env  # ty: ignore[invalid-return-type]

    warnings.warn(
        (
            f"{LOG_LEVEL_ENV}={env!r} is not a valid log level."
            f" Expected one of: {', '.join(LOG_LEVELS)}."
            f" Falling back to {DEFAULT_ROOT_LEVEL!r}."
        ),
        AmoxConfigWarning,
        stacklevel=2,
    )
    return DEFAULT_ROOT_LEVEL
