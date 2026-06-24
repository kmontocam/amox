"""Environment variable conventions and resolution logic."""

import logging
import os
import typing as t
import warnings

from amox.types_ import LogFormat, LogLevel
from amox.warnings_ import AmoxConfigWarning

LOG_LEVELS: set[LogLevel] = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
    "NOTSET",
}
"""
Log level names.
"""

LOG_FORMATS: set[LogFormat] = {"json", "logfmt"}
"""
Valid log format names.
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

FORMAT_ENV = "AMOX_FORMAT"
"""
Convention environment variable name to configure log format.
"""

LEVEL_ENV = "AMOX_LEVEL"
"""
Convention environment variable name to configure the root logger level.
"""

QUEUE_ENV = "AMOX_QUEUE"
"""
Convention environment variable name to enable/disable non-blocking I/O handlers.
"""

NAMESPACE_LEVEL_ENV = "AMOX_NAMESPACE_LEVEL"
"""
Convention environment variable name to configure the level of the managed
namespace logger (`name=` option in `setup()`/`config()`).
"""

EXISTING_LEVEL_ENV = "AMOX_EXISTING_LEVEL"
"""
Convention environment variable name to configure the level of third-party
loggers (`loggers=` option in `setup()`/`config()`).
"""

DEFAULT_FORMAT: LogFormat = "logfmt"
"""
Fallback log format when `AMOX_FORMAT` is unset.
"""

DEFAULT_LEVEL: LogLevel = "WARNING"
"""
Fallback log level when `AMOX_LEVEL` is unset.

Default matches Python's stdlib `logging` module where the root logger is created with
`WARNING` and the internal `lastResort` handler defaults to `WARNING`: this keeps
third-party noise silent while surfacing warnings, errors, and critical events. Python's
logging HOWTO regards this as *"the best default behavior"*.

Reference:
    - `https://docs.python.org/3/library/logging.html#logging.Logger.setLevel`
    - `https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library`
"""

DEFAULT_NAMESPACE_LEVEL: LogLevel = "DEBUG"
"""
Fallback level for the managed namespace logger when `AMOX_NAMESPACE_LEVEL` is unset.

Defaults to `DEBUG` so that the application's own loggers are verbose while
third-party loggers stay quiet at the root's level.
"""

DEFAULT_EXISTING_LEVEL: LogLevel = "WARNING"
"""
Fallback level for third-party existing loggers listed via `loggers=` when
`AMOX_EXISTING_LEVEL` is unset.
"""

DEFAULT_QUEUE = True
"""
Fallback usage of queue handler when `AMOX_QUEUE` is unset.
"""

LEVEL_DEFAULTS: dict[str, LogLevel] = {
    LEVEL_ENV: DEFAULT_LEVEL,
    NAMESPACE_LEVEL_ENV: DEFAULT_NAMESPACE_LEVEL,
    EXISTING_LEVEL_ENV: DEFAULT_EXISTING_LEVEL,
}
"""
Mapping of `AMOX_*_LEVEL` environment variable names to their fallback defaults.
"""


def resolve_format() -> LogFormat:
    """
    Resolve log format from `AMOX_FORMAT`.

    When the environment variable is not set, falls back to `DEFAULT_FORMAT`.
    Invalid values trigger an `AmoxConfigWarning` and fall back to the default.
    """
    env = os.environ.get(FORMAT_ENV)
    if env is None:
        return DEFAULT_FORMAT
    normalized = env.strip().lower()
    if normalized in LOG_FORMATS:
        return normalized  # ty: ignore[invalid-return-type]

    warnings.warn(
        (
            f"{FORMAT_ENV}={env!r} is not valid."
            f" Expected one of: {', '.join(sorted(LOG_FORMATS))}."
            f" Falling back to {DEFAULT_FORMAT!r}."
        ),
        AmoxConfigWarning,
        stacklevel=2,
    )
    return DEFAULT_FORMAT


def resolve_level(env_name: str = LEVEL_ENV) -> LogLevel:
    """
    Resolve logger level from an `AMOX_*_LEVEL` environment variable.

    When the environment variable is not set, falls back to the corresponding
    default from `LEVEL_DEFAULTS`. Invalid values trigger an `AmoxConfigWarning`
    and fall back to the default.

    `env_name` must be a key in `LEVEL_DEFAULTS`. Defaults to `LEVEL_ENV`
    (root logger level).

    Raises:
        ValueError: if `env_name` is not a registered level environment
        variable.

    Reference:
        `https://docs.python.org/3/library/logging.html#logging-levels`

    """
    if env_name not in LEVEL_DEFAULTS:
        msg = (
            f"{env_name!r} is not a registered level environment variable."
            f" Expected one of: {', '.join(sorted(LEVEL_DEFAULTS))}."
        )
        raise ValueError(msg)
    default = LEVEL_DEFAULTS[env_name]
    env = os.environ.get(env_name)
    if env is None:
        return default
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
            f"{env_name}={env!r} is not a valid log level."
            f" Expected one of: {', '.join(sorted(LOG_LEVELS))}."
            f" Falling back to {default!r}."
        ),
        AmoxConfigWarning,
        stacklevel=2,
    )
    return default


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
