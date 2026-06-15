"""Environment variable conventions and resolution logic."""

import logging
import os
import typing as t
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

LOG_QUEUE_ENV = "AMOX_QUEUE"
"""
Convention environment variable name to enable/disable queue-based I/O.
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

BOOL_TRUTHY: frozenset[t.Literal["1", "true"]] = frozenset({"1", "true"})
"""
Accepted truthy values for boolean environment variables.

Reference:
    `https://pkg.go.dev/strconv#ParseBool`
"""

BOOL_FALSY: frozenset[t.Literal["0", "false"]] = frozenset({"0", "false"})
"""
Accepted falsy values for boolean environment variables.

Reference:
    `https://pkg.go.dev/strconv#ParseBool`
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
    normalized = env.strip().lower()
    if normalized in LOG_FORMATS:
        return normalized  # ty: ignore[invalid-return-type]

    warnings.warn(
        (
            f"{LOG_FORMAT_ENV}={env!r} is not valid."
            f" Expected one of: {', '.join(sorted(LOG_FORMATS))}."
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

    Reference:
        - `https://docs.python.org/3/library/logging.html#logging-levels`
    """
    env = os.environ.get(LOG_LEVEL_ENV)
    if env is None:
        return DEFAULT_ROOT_LEVEL
    stripped = env.strip()
    normalized = stripped.upper()
    if normalized in LOG_LEVELS:
        return normalized  # ty: ignore[invalid-return-type]
    if stripped.isdigit():
        name = logging.getLevelName(int(stripped))
        if name in LOG_LEVELS:
            return name  # ty: ignore[invalid-return-type]

    warnings.warn(
        (
            f"{LOG_LEVEL_ENV}={env!r} is not a valid log level."
            f" Expected one of: {', '.join(sorted(LOG_LEVELS))}."
            f" Falling back to {DEFAULT_ROOT_LEVEL!r}."
        ),
        AmoxConfigWarning,
        stacklevel=2,
    )
    return DEFAULT_ROOT_LEVEL


def resolve_bool(env_name: str) -> bool | None:
    """
    Resolve a boolean from the given environment variable.

    Returns `None` when the variable is unset.
    Invalid values trigger an `AmoxConfigWarning` and return `None`.

    Reference:
        `https://pkg.go.dev/strconv#ParseBool`
    """
    env = os.environ.get(env_name)
    if env is None:
        return None
    normalized = env.strip().lower()
    if normalized in BOOL_TRUTHY:
        return True
    if normalized in BOOL_FALSY:
        return False

    truthy = ", ".join(sorted(BOOL_TRUTHY))
    falsy = ", ".join(sorted(BOOL_FALSY))
    warnings.warn(
        (
            f"{env_name}={env!r} is not a valid boolean."
            f" Expected one of: {truthy} (truthy) or {falsy} (falsy)."
            f" Ignoring."
        ),
        AmoxConfigWarning,
        stacklevel=2,
    )
    return None
