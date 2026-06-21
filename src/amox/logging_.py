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

import amox
from amox.formatters import AmoxFormatter, create_formatter
from amox.handlers import LiveQueueHandler, create_handler, has_handler
from amox.types_ import (
    ConfigOptions,
    DictConfig,
    FormatterOptions,
    LogFormat,
    LoggerConfig,
    LogLevel,
    SetupOptions,
)
from amox.warnings_ import AmoxFormatWarning

DEFAULT_EXISTING_LOGGER_LEVEL: LogLevel = "WARNING"
"""
Default log level on setup when viewing logs of third party packages.
"""

DEFAULT_LOGGER_LEVEL: LogLevel = "DEBUG"
"""
Default log level for a managed logger.
"""

log = logging.getLogger(amox.__name__)
"""
Library logger for internal messages.
"""


def setup(**opts: t.Unpack[SetupOptions]) -> None:
    """
    Apply configuration on root logger using a `logging.StreamHandler`.

    Defines `stderr` as the preferred stream for logging output, designed so **all
    loggers** in the process adhere to convention and emit semi-structured output.
    Intended to be used on program's entrypoint before the instantiation of any logger.

    Note:
        Beware the order in which modules are loaded, existing loggers created via
        `get_logger` before call will mutate in-place and delegate configuration to
        the root logger.

    Reference:
        `https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library`
        `https://pubs.opengroup.org/onlinepubs/9699919799/functions/stderr.html`

    """
    # early exit if no modifications and root handler already modified
    if not opts and has_handler():
        return

    cfg = config(**opts)

    logging.config.dictConfig(cfg)  # ty: ignore[invalid-argument-type]

    # remove any pre existing `get_logger`-managed stream handlers: let dictConfig rule
    # the logging tree.
    for logger_name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        handlers = [h for h in logger.handlers if h.name and h.name == amox.__name__]
        if handlers:
            msg = f"dropping {logger_name=} formatter: overwritten by root's config."
            log.warning(msg)
            for h in handlers:
                logger.removeHandler(h)
            logger.propagate = True

    return


def config(**opts: t.Unpack[ConfigOptions]) -> DictConfig:
    """
    Resolve `dictConfig`'s configuration.

    Apply options and environment conventions to produce a compliant mapping
    for `logging.config.dictConfig`.
    """
    cfg = copy.deepcopy(dict_config())

    # forward formatter opts into baked-in formatter factory
    formatter_cfg: dict[str, object] = cfg["formatters"][amox.__name__]  # ty: ignore[invalid-assignment]

    formatter_cfg.update(
        {key: opts.get(key) for key in set(opts) & AmoxFormatter.configurable},
    )

    # override format if explicitly passed (bypass env/default)
    formatter_cfg.update(format=fmt) if (fmt := opts.get("format")) else None
    formatter_cfg.update({".": {"tz": tz}}) if (tz := opts.get("tz")) else None

    # explicit queue overrides env var / default
    cfg["handlers"][amox.__name__]["queue"] = opts.get("queue")  # ty: ignore[invalid-assignment]

    # explicit level overrides env var / default
    if level := opts.get("level"):
        cfg["root"]["level"] = level

    loggers: dict[str, LoggerConfig] = {}
    # logger namespace (tree): set to DEBUG.
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

    return cfg


def get_logger(
    name: str | None = None,
    *,
    queue: bool | None = None,
    level: LogLevel | int | None = None,
    log_format: LogFormat | None = None,
    handlers: list[logging.Handler] | None = None,
    **opts: t.Unpack[FormatterOptions],
) -> logging.Logger:
    """
    Return logger with a `stderr` `logging.Streamhandler` with structured format.

    Args:
        name: proxy for `logging`'s `getLogger()` name parameter.
        queue: wrap all logger handlers inside a `logging.handlers.QueueHandler`
            for non-blocking I/O. When omitted, reads from `AMOX_QUEUE`
            environment variable, defaults to `True`.
        level: proxy for `logging.Logger`'s bound `setLevel()` level parameter.
            Defaults to `'DEBUG'`.
        log_format: schema on read format. When omitted, reads from
            `AMOX_LOG_FORMAT` environment variable, defaults to `'logfmt'`.
        handlers: additional handlers to append into the logger besides the base
            `logging.StreamHandler`.

    Note:
        Calls with the same name returns the existing logger without duplicating
        handlers. Formatting options on repeat calls or when `setup()` is active are
        ignored.

        Usage can be independent to `setup()` with standalone calls, as it also works
        on initialized environments. Non configured processes via `setup()` with queue
        handlers enabled **will spawn a thread for every logger created**, which may
        lead to unexpected compute usage.

    Reference:
        `https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library`
        `https://pubs.opengroup.org/onlinepubs/9699919799/functions/stderr.html`

    """
    logger = logging.getLogger(name)
    configured_by_setup = has_handler()
    configured_by_get_logger = not configured_by_setup and has_handler(logger=logger)

    if configured_by_get_logger:
        # check against defaults
        if log_format is not None or queue or opts or handlers or level:
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

    formatter = create_formatter(log_format, **opts)
    handlers = handlers or list[logging.Handler]()
    level = level or DEFAULT_LOGGER_LEVEL

    logger.setLevel(level)

    for h in handlers:
        h.formatter = formatter

    if configured_by_setup:
        root = next(h for h in logging.root.handlers if h.name == amox.__name__)
        if isinstance(root, LiveQueueHandler) and (listener := root.listener):
            # append to queue handler to produce non blocking I/O regardless of the
            # logger on the tree.
            [h.addFilter(lambda log: log.name == name) for h in handlers]
            listener.handlers = (*listener.handlers, *handlers)
        else:
            # prevent creation of amox handler, append given and early exit
            [logger.addHandler(h) for h in handlers]
        return logger

    handler = create_handler(queue=queue, formatter=formatter, handlers=handlers)
    logger.addHandler(handler)

    if not isinstance(handler, LiveQueueHandler):
        [logger.addHandler(h) for h in handlers]

    if name is not None:
        logger.propagate = False

    return logger


@functools.cache
def dict_config() -> DictConfig:
    """Load the bundled base dictConfig from JSON."""
    config_file = pathlib.Path(__file__).parent / "dictConfig.json"
    with pathlib.Path.open(config_file) as f:
        return json.load(f)
