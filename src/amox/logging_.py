"""Core logging APIs."""

import copy
import functools
import json
import logging
import logging.config
import pathlib
import types
import typing as t
import warnings

from amox.env import resolve_level
from amox.formatters import AmoxFormatter, create_formatter
from amox.handlers import LiveQueueHandler
from amox.types_ import (
    DictConfig,
    FormatterOptions,
    LogFormat,
    LoggerConfig,
    LogLevel,
    SetupOptions,
)
from amox.warnings_ import AmoxFormatWarning

LIB = f"{__package__}"
"""
Library name, reference for `dictConfig`'s custom objects.
"""


DEFAULT_EXISTING_LOGGER_LEVEL: LogLevel = "WARNING"
"""
Default log level on setup when viewing logs of third party packages.
"""

DEFAULT_QUEUE_HANDLER_NAME = f"{LIB}.{LiveQueueHandler.__name__}"
"""
Default handler (queue) name included on `dictConfig`.
"""

DEFAULT_STREAM_HANDLER_NAME = f"{LIB}.{logging.StreamHandler.__name__}"
"""
Default handler name set on `StreamHandler` instances.
"""

log = logging.getLogger(LIB)
"""
Library logger for internal messages.
"""


def setup(**opts: t.Unpack[SetupOptions]) -> None:
    """
    Configure root logger with schema based formatter.

    Appends a `StreamHandler` on the root logger. All loggers in the process inherit
    the handler and emit semi-structured output.
    """
    # early exit if no modifications and root handler already modified
    if not opts and has_handler():
        return

    cfg = config()

    # forward formatter opts into baked-in formatter factory
    formatter_cfg: dict[str, object] = cfg["formatters"][LIB]  # ty: ignore[invalid-assignment]  # pyright: ignore[reportAssignmentType, reportTypedDictNotRequiredAccess]

    formatter_cfg.update(
        {key: opts.get(key) for key in set(opts) & AmoxFormatter.configurable},
    )

    # override format if explicitly passed (bypass env/default)
    formatter_cfg.update(format=fmt) if (fmt := opts.get("format")) else None
    formatter_cfg.update({".": {"tz": tz}}) if (tz := opts.get("tz")) else None

    use_queue = opts.get("queue", True)
    if not use_queue:
        _ = cfg["handlers"].pop(DEFAULT_QUEUE_HANDLER_NAME)  # type: ignore[misc]
        cfg["root"]["handlers"] = [LIB]  # pyright: ignore[reportTypedDictNotRequiredAccess]

    # explicit level overrides env var / default
    if level := opts.get("level"):
        cfg["root"]["level"] = level  # pyright: ignore[reportTypedDictNotRequiredAccess]

    loggers: dict[str, LoggerConfig] = {}
    # logger namespace (tree): promote to DEBUG.
    if name := opts.get("name"):
        loggers[name] = {"level": "DEBUG"}

    for entry in opts.get("loggers", []):
        if isinstance(entry, (str, types.ModuleType)):
            entry_name = (
                entry.__name__ if isinstance(entry, types.ModuleType) else entry
            )
            loggers[entry_name] = {"level": DEFAULT_EXISTING_LOGGER_LEVEL}
        else:
            mod = entry["module"]
            entry_name = mod.__name__ if isinstance(mod, types.ModuleType) else mod
            loggers[entry_name] = {"level": entry["level"]}

    cfg["loggers"] = loggers

    logging.config.dictConfig(cfg)  # ty: ignore[invalid-argument-type]  # pyright: ignore[reportArgumentType]

    # remove any pre existing `get_logger`-managed stream handlers: let dictConfig rule
    # the logging tree.
    for logger_name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        handlers = [h for h in logger.handlers if h.name and h.name.startswith(LIB)]
        if handlers:
            msg = f"dropping {logger_name=} formatter: overwritten by root's config."
            log.warning(msg)
            for h in handlers:
                logger.removeHandler(h)
            logger.propagate = True

    return


def config() -> DictConfig:
    """Return amox's `dictConfig` mapping with resolved root level."""
    cfg = copy.deepcopy(read_config())
    cfg["root"]["level"] = resolve_level()  # pyright: ignore[reportTypedDictNotRequiredAccess]
    return cfg


def get_logger(
    name: str | None = None,
    *,
    level: LogLevel | int = logging.DEBUG,
    log_format: LogFormat | None = None,
    handlers: list[logging.Handler] | None = None,
    **opts: t.Unpack[FormatterOptions],
) -> logging.Logger:
    """
    Return a logger with structured formatting attached.

    Note:
        Calls with the same name returns the existing logger without duplicating
        handlers. Formatting options on repeat calls or when `setup()` is active are
        ignored with an `AmoxFormatWarning`.

        When neither `setup()` nor a prior call configured the logger, a StreamHandler
        with an AmoxFormatter is attached and propagation is disabled to prevent double
        output.

    """
    logger = logging.getLogger(name)
    configured_by_setup = has_handler()
    configured_by_get_logger = not configured_by_setup and has_handler(logger=logger)

    if configured_by_get_logger:
        # check against defaults
        if (
            log_format is not None
            or opts
            or handlers is not None
            or level != logging.DEBUG
        ):
            warnings.warn(
                f"options ignored on already configured logger {name!r}",
                AmoxFormatWarning,
                stacklevel=2,
            )
        return logger

    has_formatting = log_format is not None or opts
    if configured_by_setup and has_formatting:
        warnings.warn(
            f"formatting options ignored on configured setup, logger {name!r}",
            AmoxFormatWarning,
            stacklevel=2,
        )

    if configured_by_setup:
        for h in handlers or []:
            logger.addHandler(h)
        logger.setLevel(level)
        # early exit on stream handler because of setup
        return logger

    stream = logging.StreamHandler()
    stream.name = DEFAULT_STREAM_HANDLER_NAME
    stream.setFormatter(create_formatter(log_format, **opts))  # ty: ignore[no-matching-overload]
    logger.addHandler(stream)
    for h in handlers or []:
        logger.addHandler(h)
    logger.setLevel(level)
    if name is not None:
        logger.propagate = False

    return logger


def has_handler(prefix: str = LIB, *, logger: logging.Logger | None = None) -> bool:
    """
    Whether any handler on the target logger is named after a given prefix.

    `dictConfig` sets `handler.name` to the dict key, so handlers installed via
    `setup()` will have names starting with the package name. Defaults to the root
    logger.
    """
    target = logger or logging.getLogger()
    return any(h.name and h.name.startswith(prefix) for h in target.handlers)


@functools.cache
def read_config() -> DictConfig:
    """Load and cache the bundled dictConfig JSON file."""
    config_file = pathlib.Path(__file__).parent / "dictConfig.json"
    with open(config_file) as f:  # noqa: PTH123
        return json.load(f)
