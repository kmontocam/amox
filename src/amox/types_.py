"""Library types."""

import datetime as dt
import types
import typing as t
from collections import abc

type Logfmt = t.Literal["logfmt"]
type Json = t.Literal["json"]

type LogFormat = Logfmt | Json

type LogLevel = t.Literal[
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
    "NOTSET",
]

type LogRecordAttr = t.Literal[
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "message",
    "module",
    "msecs",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "taskName",
    "thread",
    "threadName",
]
"""
All instance attributes of a `logging.LogRecord`
"""

type IncludeMode = t.Literal["minimal", "verbose", "all"]
"""
Configuration mode for formatters.

- `'minimal'`: `[created, levelname, name, msg]`
- `'verbose'`: `[created, levelname, name, msg, filename, lineno, funcName, threadName,
    processName]`
- `'all'`: all attributes from `logging.LogRecord`

All levels include `exc_info` if message object is an exception.
"""

type IncludeFields = IncludeMode | list[LogRecordAttr]
"""
Fields to view on a record. Convention or explicit attributes.

List individual attributes or provide a convention.
"""

type FormatStyle = t.Literal["%", "{", "$"]
"""
Base `logging.Formatter` format constructor parameter.
"""


type FieldRemap = abc.Mapping[LogRecordAttr, str]
"""
Configuration map to give default attribute keys a different name.
"""

type JsonValue = (
    list[JsonValue] | dict[str, JsonValue | object] | bool | int | float | None
)

type SetupOptions = ConfigOptions


class FormatterConfig(t.TypedDict, total=False):
    """
    Standard `logging.Formatter` configuration.

    Reference:
        `https://docs.python.org/3/library/logging.html#logging.Formatter`
    """

    format: str
    datefmt: str
    style: FormatStyle
    validate: bool
    defaults: dict[str, object]


class FilterConfig(t.TypedDict, total=False):
    """
    Standard `logging.Filter` configuration.

    Reference:
        `https://docs.python.org/3/library/logging.html#logging.Filter`
    """

    name: str


StreamHandlerConfig = t.TypedDict(
    "StreamHandlerConfig",
    {
        "class": t.Required[t.Literal["logging.StreamHandler"]],
        "level": LogLevel,
        "formatter": str,
        "filters": list[str],
        "stream": str,
    },
    total=False,
)
"""
`logging.StreamHandler` configuration.

Reference:
    `https://docs.python.org/3/library/logging.handlers.html#logging.StreamHandler`
"""

FileHandlerConfig = t.TypedDict(
    "FileHandlerConfig",
    {
        "class": t.Required[t.Literal["logging.FileHandler"]],
        "level": LogLevel,
        "formatter": str,
        "filters": list[str],
        "filename": t.Required[str],
        "mode": t.Literal["a", "w", "x"],
        "encoding": str,
        "delay": bool,
        "errors": str,
    },
    total=False,
)
"""
`logging.FileHandler` configuration.

Reference:
    `https://docs.python.org/3/library/logging.handlers.html#logging.FileHandler`
"""

RotatingFileHandlerConfig = t.TypedDict(
    "RotatingFileHandlerConfig",
    {
        "class": t.Required[t.Literal["logging.handlers.RotatingFileHandler"]],
        "level": LogLevel,
        "formatter": str,
        "filters": list[str],
        "filename": t.Required[str],
        "mode": t.Literal["a", "w", "x"],
        "maxBytes": int,
        "backupCount": int,
        "encoding": str,
        "delay": bool,
        "errors": str,
    },
    total=False,
)
"""
`logging.handlers.RotatingFileHandler` configuration. Rotates log files by size.

Reference:
    `https://docs.python.org/3/library/logging.handlers.html#logging.handlers.RotatingFileHandler`
"""

TimedRotatingFileHandlerConfig = t.TypedDict(
    "TimedRotatingFileHandlerConfig",
    {
        "class": t.Required[t.Literal["logging.handlers.TimedRotatingFileHandler"]],
        "level": LogLevel,
        "formatter": str,
        "filters": list[str],
        "filename": t.Required[str],
        "when": t.Literal[
            "S",
            "M",
            "H",
            "D",
            "W0",
            "W1",
            "W2",
            "W3",
            "W4",
            "W5",
            "W6",
            "midnight",
        ],
        "interval": int,
        "backupCount": int,
        "encoding": str,
        "delay": bool,
        "utc": bool,
        "atTime": str,
        "errors": str,
    },
    total=False,
)
"""
`logging.handlers.TimedRotatingFileHandler` configuration. Rotates log files by time
interval.

Reference:
    `https://docs.python.org/3/library/logging.handlers.html#logging.handlers.TimedRotatingFileHandler`
"""

WatchedFileHandlerConfig = t.TypedDict(
    "WatchedFileHandlerConfig",
    {
        "class": t.Required[t.Literal["logging.handlers.WatchedFileHandler"]],
        "level": LogLevel,
        "formatter": str,
        "filters": list[str],
        "filename": t.Required[str],
        "mode": t.Literal["a", "w", "x"],
        "encoding": str,
        "delay": bool,
        "errors": str,
    },
    total=False,
)
"""
`logging.handlers.WatchedFileHandler` configuration. Watches the log file for external
rotation. Unix only.

Reference:
    `https://docs.python.org/3/library/logging.handlers.html#logging.handlers.WatchedFileHandler`
"""

SocketHandlerConfig = t.TypedDict(
    "SocketHandlerConfig",
    {
        "class": t.Required[t.Literal["logging.handlers.SocketHandler"]],
        "level": LogLevel,
        "formatter": str,
        "filters": list[str],
        "host": t.Required[str],
        "port": t.Required[int],
    },
    total=False,
)
"""
`logging.handlers.SocketHandler` configuration. Sends pickled log records over TCP.

Reference:
    `https://docs.python.org/3/library/logging.handlers.html#logging.handlers.SocketHandler`
"""

DatagramHandlerConfig = t.TypedDict(
    "DatagramHandlerConfig",
    {
        "class": t.Required[t.Literal["logging.handlers.DatagramHandler"]],
        "level": LogLevel,
        "formatter": str,
        "filters": list[str],
        "host": t.Required[str],
        "port": t.Required[int],
    },
    total=False,
)
"""
`logging.handlers.DatagramHandler` configuration. Sends pickled log records over UDP.

Reference:
    `https://docs.python.org/3/library/logging.handlers.html#logging.handlers.DatagramHandler`
"""

SysLogHandlerConfig = t.TypedDict(
    "SysLogHandlerConfig",
    {
        "class": t.Required[t.Literal["logging.handlers.SysLogHandler"]],
        "level": LogLevel,
        "formatter": str,
        "filters": list[str],
        "address": str | tuple[str, int],
        "facility": int,
        "socktype": str,
    },
    total=False,
)
"""
`logging.handlers.SysLogHandler` configuration. Sends log records to a Unix syslog or
remote syslog daemon.

Reference:
    `https://docs.python.org/3/library/logging.handlers.html#logging.handlers.SysLogHandler`
"""

NTEventLogHandlerConfig = t.TypedDict(
    "NTEventLogHandlerConfig",
    {
        "class": t.Required[t.Literal["logging.handlers.NTEventLogHandler"]],
        "level": LogLevel,
        "formatter": str,
        "filters": list[str],
        "appname": t.Required[str],
        "dllname": str,
        "logtype": t.Literal["Application", "System", "Security"],
    },
    total=False,
)
"""
`logging.handlers.NTEventLogHandler` configuration. Windows only.

Reference:
    `https://docs.python.org/3/library/logging.handlers.html#logging.handlers.NTEventLogHandler`
"""

SMTPHandlerConfig = t.TypedDict(
    "SMTPHandlerConfig",
    {
        "class": t.Required[t.Literal["logging.handlers.SMTPHandler"]],
        "level": LogLevel,
        "formatter": str,
        "filters": list[str],
        "mailhost": t.Required[str | tuple[str, int]],
        "fromaddr": t.Required[str],
        "toaddrs": t.Required[str | list[str]],
        "subject": t.Required[str],
        "credentials": tuple[str, str],
        "secure": list[str],
        "timeout": float,
    },
    total=False,
)
"""
`logging.handlers.SMTPHandler` configuration. Sends log records via email using SMTP.

Reference:
    `https://docs.python.org/3/library/logging.handlers.html#logging.handlers.SMTPHandler`
"""

MemoryHandlerConfig = t.TypedDict(
    "MemoryHandlerConfig",
    {
        "class": t.Required[t.Literal["logging.handlers.MemoryHandler"]],
        "level": LogLevel,
        "formatter": str,
        "filters": list[str],
        "capacity": t.Required[int],
        "flushLevel": int,
        "target": str,
        "flushOnClose": bool,
    },
    total=False,
)
"""
`logging.handlers.MemoryHandler` configuration. Buffers records in memory and flushes to
a target handler.

Reference:
    `https://docs.python.org/3/library/logging.handlers.html#logging.handlers.MemoryHandler`
"""

HTTPHandlerConfig = t.TypedDict(
    "HTTPHandlerConfig",
    {
        "class": t.Required[t.Literal["logging.handlers.HTTPHandler"]],
        "level": LogLevel,
        "formatter": str,
        "filters": list[str],
        "host": t.Required[str],
        "url": t.Required[str],
        "method": t.Literal["GET", "POST"],
        "secure": bool,
        "credentials": tuple[str, str],
        "context": str,
    },
    total=False,
)
"""
`logging.handlers.HTTPHandler` configuration. Sends log records to a web server via
HTTP.

Reference:
    `https://docs.python.org/3/library/logging.handlers.html#logging.handlers.HTTPHandler`
"""

QueueHandlerConfig = t.TypedDict(
    "QueueHandlerConfig",
    {
        "class": t.Required[t.Literal["logging.handlers.QueueHandler"]],
        "level": LogLevel,
        "formatter": str,
        "filters": list[str],
        "queue": object,
        "handlers": list[str],
        "respect_handler_level": bool,
        "listener": str,
    },
    total=False,
)
"""
`logging.handlers.QueueHandler` configuration. Sends log records to a queue.

Reference:
    `https://docs.python.org/3/library/logging.handlers.html#logging.handlers.QueueHandler`
"""

NullHandlerConfig = t.TypedDict(
    "NullHandlerConfig",
    {
        "class": t.Required[t.Literal["logging.NullHandler"]],
        "level": LogLevel,
        "formatter": str,
        "filters": list[str],
    },
    total=False,
)
"""
`logging.NullHandler` configuration. A no-op handler.

Reference:
    `https://docs.python.org/3/library/logging.handlers.html#logging.NullHandler`
"""


class AnyHandlerConfig(t.TypedDict, total=False):
    """
    Handler configuration using the `()` protocol for managed handlers.

    Covers handlers created via `dictConfig`'s `()` syntax, where arbitrary keyword
    arguments are passed to the callable.
    """

    __extra_items__: object


type HandlerConfig = (
    StreamHandlerConfig
    | FileHandlerConfig
    | RotatingFileHandlerConfig
    | TimedRotatingFileHandlerConfig
    | WatchedFileHandlerConfig
    | SocketHandlerConfig
    | DatagramHandlerConfig
    | SysLogHandlerConfig
    | NTEventLogHandlerConfig
    | SMTPHandlerConfig
    | MemoryHandlerConfig
    | HTTPHandlerConfig
    | QueueHandlerConfig
    | NullHandlerConfig
    | AnyHandlerConfig
)


class LoggerConfig(t.TypedDict, total=False):
    """
    Configuration for a named logger.

    Reference:
        `https://docs.python.org/3/library/logging.config.html#dictionary-schema-details`
    """

    level: LogLevel | int
    propagate: bool
    filters: list[str]
    handlers: list[str]


class RootLoggerConfig(t.TypedDict, total=False):
    """
    Configuration for the root logger.

    Reference:
        `https://docs.python.org/3/library/logging.config.html#dictionary-schema-details`
    """

    level: LogLevel
    filters: list[str]
    handlers: list[str]


class DictConfig(t.TypedDict, total=False):
    """
    Python `logging.config.dictConfig()` configuration dictionary.

    Reference:
        `https://docs.python.org/3/library/logging.config.html#configuration-dictionary-schema`
    """

    version: t.Required[t.Literal[1]]
    disable_existing_loggers: bool
    incremental: bool
    formatters: dict[str, FormatterConfig]
    filters: dict[str, FilterConfig]
    handlers: t.Required[dict[str, HandlerConfig]]
    loggers: dict[str, LoggerConfig]
    root: RootLoggerConfig


class LoggerLevelConfig(t.TypedDict, total=False):
    """Per-logger level override ."""

    module: t.Required[types.ModuleType | str]
    level: t.Required[LogLevel | int]


class FormatterOptions(t.TypedDict, total=False):
    """Shared formatter options."""

    datefmt: str | None
    """
    strftime format for timestamps.
    """

    include: IncludeFields
    """
    Fields to include in output (`'minimal'`, `'verbose'`, `'all'`, or explicit list of
    `LogRecordAttr`).
    """

    snake_case: bool
    """
    Whether to snake_case output keys.
    """

    field_remap: FieldRemap
    """
    Mapping to rename `LogRecord` attribute keys.
    """

    tz: dt.tzinfo
    """
    Timezone for timestamp formatting.
    """


class ConfigOptions(FormatterOptions, total=False):
    """Logging configuration options."""

    name: str
    """
    System logger namespace. All loggers on the tree are set to
    `DEBUG` while root and packages stay at the configured level.

    Typically a top-level package name (e.g. `__name__`).
    """

    format: LogFormat
    """
    Override the log format (`'logfmt'` or `'json'`). When omitted, reads from
    `AMOX_LOG_FORMAT` env var, defaulting to `'logfmt'`.
    """

    level: LogLevel
    """
    Override the root logger level. When omitted, reads from `AMOX_LOG_LEVEL`
    env var, defaulting to `'WARNING'`.
    """

    loggers: list[types.ModuleType | str | LoggerLevelConfig]
    """
    List of third-party modules or logger names to cap at a specific level. Strings and
    modules default to `WARNING`. Dicts with `{"module": ..., "level": ...}` set an
    explicit level.
    """

    queue: bool
    """
    Whether to wrap the handler in a `QueueHandler` for non-blocking I/O. When omitted,
    reads from `AMOX_QUEUE` env var, defaulting to `True`.
    """
