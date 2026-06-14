"""Schema on read formatters."""

import datetime as dt
import json
import logging
import re
import typing as t

from amox.env import resolve_format
from amox.types_ import (
    FieldRemap,
    FormatterOptions,
    IncludeFields,
    Json,
    Logfmt,
    LogFormat,
    LogRecordAttr,
)

DEL_CHAR = 0x7F
"""
ASCII DEL character ordinal.
"""

LOG_RECORD_BUILTIN_ATTRS: set[LogRecordAttr] = set(
    logging.makeLogRecord({"message": "", "asctime": ""}).__dict__.keys(),
)  # ty: ignore[invalid-assignment]
"""
`logging.LogRecord` instance attributes to enrich logs.

Note:
    `message` and `asctime` are seeded, since `makeLogRecord` materializes them during
    `Formatter.format()`.
"""


DEFAULT_FIELD_REMAP: FieldRemap = {
    "created": "ts",
    "levelname": "level",
    "name": "logger",
    "msg": "msg",
    "exc_info": "exception",
}
"""
Default rename convention of `LogRecordAttr`.
"""

DEFAULT_INCLUDE: tuple[LogRecordAttr, ...] = (
    "created",
    "levelname",
    "name",
    "msg",
    "exc_info",
)

VERBOSE_INCLUDE: tuple[LogRecordAttr, ...] = (
    *DEFAULT_INCLUDE,
    "filename",
    "lineno",
    "funcName",
    "threadName",
    "processName",
)

ALL_EXCLUDE: set[LogRecordAttr] = {
    "args",
    "exc_text",
    "relativeCreated",
    "msecs",
}
"""
Always excluded attributes from log record.
"""


class AmoxFormatter(logging.Formatter):
    """Base formatter with shared field extraction logic."""

    configurable: frozenset[
        t.Literal[
            "datefmt",
            "include",
            "snake_case",
            "field_remap",
        ]
    ] = frozenset(
        {
            "datefmt",
            "include",
            "snake_case",
            "field_remap",
        },
    )
    tz: dt.tzinfo | None = None

    def __init__(  # noqa: PLR0913
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: t.Literal["%", "{", "$"] = "%",
        validate: bool = True,  # noqa: FBT001, FBT002
        *,
        defaults: dict[str, object] | None = None,
        include: IncludeFields = "minimal",
        snake_case: bool = True,
        field_remap: FieldRemap = DEFAULT_FIELD_REMAP,
    ) -> None:
        """
        Initialize the structured formatter.

        Args:
            fmt: format string for `logging.Formatter` (e.g. `'%(message)s'`).
                Included for protocol, not typically used with schema formatters.
            datefmt: strftime format for `LogRecord.created` timestamp.
            style: format string style character (`%`, `{`, or `$`).
            validate: whether to validate the format string.
            defaults: default values merged into every record's `__dict__`.
            include: list of attributes of a record to include, or string based
                convention.
            snake_case: whether to snake_case the keys from the compiled records.
                Applies to field_remap values as well.
            field_remap: mapping to convert attribute keys to a different name

        """
        super().__init__(
            fmt=fmt,
            datefmt=datefmt,
            style=style,
            validate=validate,
            defaults=defaults,
        )
        self.snake_case: bool = snake_case
        self.field_remap: FieldRemap = field_remap

        self.include: tuple[LogRecordAttr, ...] = self.includes(include)
        self.field_remap_keys: list[LogRecordAttr] = list(field_remap.keys())

    def includes(self, fields: IncludeFields) -> tuple[LogRecordAttr, ...]:
        """Resolve record attributes to include on the record."""
        if isinstance(fields, list):
            return tuple(fields)
        if fields == "minimal":
            return DEFAULT_INCLUDE
        if fields == "verbose":
            return VERBOSE_INCLUDE

        return tuple(  # "all"
            LOG_RECORD_BUILTIN_ATTRS - ALL_EXCLUDE,
        )

    def output_key(self, source: str) -> str:
        """
        Resolve the output key name for a `LogRecord` attribute.

        Apply's `field_remap` rename if present, snake cases field if configured.
        """
        if source in self.field_remap_keys:
            source = self.field_remap[source]  # ty: ignore[invalid-argument-type]

        return self.to_snake(source) if self.snake_case else source

    def value_from_record(
        self,
        record: logging.LogRecord,
        source: LogRecordAttr,
    ) -> str | None:
        """
        Extract a value from a `LogRecord`.

        Apply dedicated reader to attributes that are enhanced by standard record
        formatters or custom.
        """
        if source == "msg":
            return record.getMessage()
        if source == "created":
            return self.format_timestamp(record.created)

        if source == "exc_info":
            return (
                self.formatException(exc)
                if (exc := record.exc_info)
                else record.exc_text
            )
        return getattr(record, source, None)

    def compile_record(self, record: logging.LogRecord) -> dict[str, object]:
        """
        Build dictionary from a `LogRecord`, ready to deserialize.

        Pre-process a raw log record object with configuration options. Produce
        a mapping ready for formatting.
        """
        payload: dict[str, object] = {}

        for key in self.include:
            val = self.value_from_record(record, key)
            if key == "exc_info" and val is None:
                continue
            payload[self.output_key(key)] = val

        payload.update(
            {
                key: val
                for key, val in record.__dict__.items()
                if key not in LOG_RECORD_BUILTIN_ATTRS
            },
        )

        return payload

    def format_timestamp(self, created: float) -> str:
        """
        Format a unix timestamp using `datefmt`.

        When `tz` is set, formats in that timezone. UTC gets a `Z` suffix.
        Defaults to local time with ISO 8601 format.
        """
        timestamp = dt.datetime.fromtimestamp(created, tz=dt.UTC)
        if self.tz is not None:
            timestamp = timestamp.astimezone(self.tz)
        else:
            timestamp = timestamp.astimezone()
        if self.datefmt:
            return timestamp.strftime(self.datefmt)
        iso = timestamp.isoformat()
        if self.tz == dt.UTC:
            return iso.replace("+00:00", "Z")
        return iso

    @staticmethod
    def to_snake(camel: str) -> str:
        """
        Convert a camelCase string to snake_case.

        Reference:
            `https://github.com/pydantic/pydantic/blob/main/pydantic/alias_generators.py`
        """
        snake = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", camel)
        snake = re.sub(r"([a-z])([A-Z])", r"\1_\2", snake)
        snake = re.sub(r"([0-9])([A-Z])", r"\1_\2", snake)
        snake = re.sub(r"([a-z])([0-9])", r"\1_\2", snake)
        return snake.replace("-", "_").lower()


class LogfmtFormatter(AmoxFormatter):
    """
    Formats log records as logfmt key=value pairs.

    Reference:
        `https://brandur.org/logfmt`
    """

    @t.override
    def format(self, record: logging.LogRecord) -> str:
        payload = self.compile_record(record)
        return " ".join(
            f"{key}={self.encode_value(val)}" for key, val in payload.items()
        )

    def encode_value(self, value: object) -> str:
        """
        Encode a value for logfmt output.

        Reference:
            `https://github.com/go-logfmt/logfmt/blob/master/encode.go`
        """
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        return self.quote(str(value))

    def quote(self, s: str) -> str:
        """Apply logfmt quoting rules to a string value."""
        if not s:
            return '""'
        if self.needs_quote(s):
            escaped = (
                s.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t")
            )
            return f'"{escaped}"'
        return s

    def needs_quote(self, s: str) -> bool:
        """
        Whether a logfmt value needs quoting.

        Reference:
            `https://github.com/go-logfmt/logfmt/blob/master/encode.go`
        """
        return any(c <= " " or c in {"=", '"', "\\"} or ord(c) == DEL_CHAR for c in s)


class JsonFormatter(AmoxFormatter):
    """Formats log records as JSON."""

    @t.override
    def format(self, record: logging.LogRecord) -> str:
        payload = self.compile_record(record)
        return json.dumps(payload, default=str)


@t.overload
def create_formatter(
    log_format: Json,
    /,
    *,
    root: bool = False,
    **opts: t.Unpack[FormatterOptions],
) -> JsonFormatter: ...


@t.overload
def create_formatter(
    log_format: Logfmt | None = None,
    /,
    *,
    root: bool = False,
    **opts: t.Unpack[FormatterOptions],
) -> LogfmtFormatter: ...


def create_formatter(
    log_format: LogFormat | None = None,
    /,
    **opts: t.Unpack[FormatterOptions],
) -> JsonFormatter | LogfmtFormatter:
    """
    Create a formatter from a format identifier string.

    Resolve the log format and return the corresponding formatter instance.
    Used mainly as the factory for `dictConfig`'s `()` protocol.
    """
    log_format = log_format or resolve_format()
    tz = opts.get("tz")
    field_remap: FieldRemap = {
        **DEFAULT_FIELD_REMAP,
        **(opts.get("field_remap") or {}),
    }
    cls = JsonFormatter if log_format == "json" else LogfmtFormatter
    formatter = cls(
        datefmt=opts.get("datefmt"),
        include=opts.get("include", "minimal"),
        snake_case=opts.get("snake_case", True),
        field_remap=field_remap,
    )
    formatter.tz = tz
    return formatter
