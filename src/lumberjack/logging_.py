"""Core logging APIs."""

import copy
import functools
import json
import logging
import logging.config
import pathlib
import types
import typing as t

from lumberjack import FormatterOptions, create_formatter
from lumberjack.formatters import LumberjackFormatter
from lumberjack.types_ import (
    DictConfig,
    LogFormat,
    LoggerConfig,
    LogLevel,
    SetupOptions,
)

LIB = f"{__package__}"
"""
Library name, reference for `dictConfig`'s custom objects.
"""

DEFAULT_EXISTING_LOGGER_LEVEL: LogLevel = "WARNING"
"""
Default log level on setup when viewing logs of third party packages.
"""


def setup(**opts: t.Unpack[SetupOptions]) -> None:
    """
    Configure the root logger with lumberjack's structured formatters.

    Installs a `StreamHandler` (optionally wrapped in a `QueueHandler`) on the root
    logger. All loggers in the process inherit the handler and emit structured output.

    The root logger level defaults to `INFO`. When `name` is provided, the named
    logger is set to `DEBUG`: giving clients full verbosity while third-party libraries
    stay at `INFO`, overridable via `loggers`.
    """
    if has_handler():
        return

    cfg = config()

    # forward formatter opts into the factory config
    formatter_cfg: dict[str, object] = cfg["formatters"][LIB]  # ty: ignore[invalid-assignment]  # pyright: ignore[reportAssignmentType, reportTypedDictNotRequiredAccess]
    for key in set(opts) & LumberjackFormatter.configurable:
        formatter_cfg[key] = opts[key]

    # override format if explicitly passed (bypass env/factory)
    if fmt := opts.get("format"):
        formatter_cfg["format"] = fmt

    # tz is non-serializable; use dictConfig's "." protocol for post-construction attr
    # setting
    if tz := opts.get("tz"):
        formatter_cfg["."] = {"tz": tz}

    use_queue = opts.get("queue", True)
    if not use_queue:
        _ = cfg["handlers"].pop(f"{LIB}.queue_handler")  # type: ignore[misc]
        cfg["root"] = {"handlers": [LIB], "level": "INFO"}

    # app namespace: promote to DEBUG while root stays at INFO
    if name := opts.get("name"):
        loggers_section: dict[str, LoggerConfig] = cfg.get("loggers", {})  # type: ignore[assignment]
        loggers_section[name] = {"level": "DEBUG"}
        cfg["loggers"] = loggers_section

    # logger level overrides
    loggers_section = cfg.get("loggers", {})  # type: ignore[assignment]

    for entry in opts.get("loggers", []):
        if isinstance(entry, (str, types.ModuleType)):
            entry_name = (
                entry.__name__ if isinstance(entry, types.ModuleType) else entry
            )
            loggers_section[entry_name] = {"level": DEFAULT_EXISTING_LOGGER_LEVEL}
        else:
            mod = entry["module"]
            entry_name = mod.__name__ if isinstance(mod, types.ModuleType) else mod
            loggers_section[entry_name] = {"level": entry["level"]}
    if loggers_section:
        cfg["loggers"] = loggers_section

    logging.config.dictConfig(cfg)  # ty: ignore[invalid-argument-type]  # pyright: ignore[reportArgumentType]
    return


def config() -> DictConfig:
    """Return lumberjack's `dictConfig` mapping."""
    return copy.deepcopy(read_config())


def get_logger(
    name: str | None = None,
    *,
    level: LogLevel | int = logging.DEBUG,
    log_format: LogFormat | None = None,
    handlers: list[logging.Handler] | None = None,
    **opts: t.Unpack[FormatterOptions],
) -> logging.Logger:
    """
    Return a logger with lumberjack's structured formatting attached.

    Creates a `StreamHandler` with a lumberjack formatter on the named logger.
    """
    logger = logging.getLogger(name)

    # early exit on scenarios that did a `setup()` call
    if has_handler():
        return logger

    # local logger
    if not logger.handlers:
        stream = logging.StreamHandler()
        stream.setFormatter(create_formatter(log_format, **opts))  # ty: ignore[no-matching-overload]
        logger.addHandler(stream)
        for h in handlers or []:
            logger.addHandler(h)
        logger.setLevel(level)

    return logger


def has_handler(name: str = LIB) -> bool:
    """
    Whether any handler on the root logger is named after a giving name.

    `dictConfig` sets `handler.name` to the dict key, so handlers installed via
    `setup()` will have names starting with the package name.
    """
    return any(h.name and h.name.startswith(name) for h in logging.getLogger().handlers)


@functools.cache
def read_config() -> DictConfig:
    """Load and cache the bundled dictConfig JSON file."""
    config_file = pathlib.Path(__file__).parent / "dictConfig.json"
    with open(config_file) as f:  # noqa: PTH123
        return json.load(f)
