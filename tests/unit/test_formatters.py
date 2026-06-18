"""Unit tests for `src.amox.formatters` module."""

import datetime as dt
import logging
import typing as t
import uuid

import pytest

from amox.formatters import (
    ALL_EXCLUDE,
    DEFAULT_FIELD_REMAP,
    DEFAULT_INCLUDE,
    LOG_RECORD_BUILTIN_ATTRS,
    VERBOSE_INCLUDE,
    AmoxFormatter,
    JsonFormatter,
    LogfmtFormatter,
    create_formatter,
)
from amox.parsers import JsonParser, LogfmtParser
from amox.types_ import (
    FormatterOptions,
    Json,
    Logfmt,
    LogFormat,
    LogRecordAttr,
)
from tests.conftest import make_exc_info, make_record

EXC_INFO: set[LogRecordAttr] = {"exc_info"}
"""
Exclude, since it's appearance it is optional.
"""

DEFAULT_KEYS: set[str] = {
    DEFAULT_FIELD_REMAP[k] for k in set(DEFAULT_INCLUDE) - EXC_INFO
}
"""
Default output keys. Excludes `exception` since it only appears on

records with an actual exception.
"""

DEFAULT_KEYS_SNAKE = DEFAULT_KEYS

VERBOSE_KEYS: set[str] = {
    DEFAULT_FIELD_REMAP.get(k, k) for k in set(VERBOSE_INCLUDE) - EXC_INFO
}
"""
Verbose output keys without snake_case.
"""

VERBOSE_KEYS_SNAKE: set[str] = {AmoxFormatter.to_snake(k) for k in VERBOSE_KEYS}
"""
Verbose output keys with snake_case.
"""

ALL_INCLUDE_KEYS: set[str] = {
    DEFAULT_FIELD_REMAP.get(k, k)
    for k in LOG_RECORD_BUILTIN_ATTRS - ALL_EXCLUDE - EXC_INFO
}
"""
All output keys.
"""

ALL_INCLUDE_KEYS_SNAKE: set[str] = {AmoxFormatter.to_snake(k) for k in ALL_INCLUDE_KEYS}
"""
All output keys snake cased.
"""


class CreateFormatter(t.Protocol):
    """`create_formatter` protocol."""

    @t.overload
    def __call__(
        self,
        log_format: Json,
        /,
        **opts: t.Unpack[FormatterOptions],
    ) -> JsonFormatter: ...

    @t.overload
    def __call__(
        self,
        log_format: Logfmt | None = None,
        /,
        **opts: t.Unpack[FormatterOptions],
    ) -> LogfmtFormatter: ...

    def __call__(
        self,
        log_format: LogFormat | None = None,
        /,
        **opts: t.Unpack[FormatterOptions],
    ) -> JsonFormatter | LogfmtFormatter:
        """Protocol for foratter factory."""
        ...


class FormatterBuilder[T: AmoxFormatter](t.Protocol):
    """
    Formatter builder fixture protocol.

    `create_formatter` protocol skipping format type, injected by callers.
    """

    def __call__(
        self,
        **opts: t.Unpack[FormatterOptions],
    ) -> T:
        """Protocol for formatter factory, with predetermined format."""
        ...


class TestFormatTimestamp:
    """Tests for timestamp formatting with timezone handling."""

    @pytest.fixture
    def formatter_builder(self) -> type[AmoxFormatter]:
        """`AmoxFormatter` constructor."""
        return AmoxFormatter

    def test_utc_produces_z_suffix(
        self,
        formatter_builder: type[AmoxFormatter],
    ) -> None:
        """UTC timezone produces ISO 8601 with Z suffix."""
        formatter = formatter_builder()
        formatter.tz = dt.UTC
        ts = formatter.format_timestamp(0.0)

        assert ts.endswith("Z")
        assert "+" not in ts

    def test_offset_timezone(
        self,
        formatter_builder: type[AmoxFormatter],
    ) -> None:
        """Non-UTC timezone produces offset suffix."""
        hours, minutes = 5, 30
        tz = dt.timezone(dt.timedelta(hours=hours, minutes=minutes))
        formatter = formatter_builder()
        formatter.tz = tz
        ts = formatter.format_timestamp(0.0)

        assert f"+0{hours}:{minutes}" in ts

    def test_custom_datefmt(
        self,
        formatter_builder: type[AmoxFormatter],
    ) -> None:
        """Custom datefmt overrides ISO 8601 output."""
        formatter = formatter_builder(datefmt="%Y-%m-%d")
        formatter.tz = dt.UTC
        ts = formatter.format_timestamp(0.0)

        assert ts == "1970-01-01"


class TestToSnake:
    """Tests for camelCase to snake_case conversion."""

    @pytest.mark.parametrize(
        ("camel", "expected"),
        [
            ("camelCase", "camel_case"),
            ("HTTPResponse", "http_response"),
            ("funcName", "func_name"),
            ("threadName", "thread_name"),
            ("processName", "process_name"),
            ("already_snake", "already_snake"),
            ("XMLHTTPRequest", "xmlhttp_request"),
            ("getHTTPSConnection", "get_https_connection"),
        ],
        ids=[
            "camel_case",
            "acronym",
            "func_name",
            "thread_name",
            "process_name",
            "already_snake",
            "multiple_acronyms",
            "acronym_in_middle",
        ],
    )
    def test_conversion(self, camel: str, expected: str) -> None:
        """Converts camelCase identifiers to snake_case."""
        assert AmoxFormatter.to_snake(camel) == expected


class TestCreateFormatter[T: AmoxFormatter]:
    """Tests for the `create_formatter` factory function."""

    @pytest.fixture
    def create_formatter(self) -> CreateFormatter:
        """`create_formatter()` factory."""
        return create_formatter

    def test_default_format(
        self,
        create_formatter: CreateFormatter,
    ) -> None:
        """Default format is to logfmt."""
        assert isinstance(create_formatter(), LogfmtFormatter)

    @pytest.mark.parametrize(
        ("log_format", "expected"),
        [
            ("json", JsonFormatter),
            ("logfmt", LogfmtFormatter),
        ],
        ids=[
            "json",
            "logfmt",
        ],
    )
    def test_format(
        self,
        log_format: LogFormat,
        expected: type[AmoxFormatter],
        create_formatter: CreateFormatter,
    ) -> None:
        """Explicit format."""
        formatter = create_formatter(log_format)
        assert isinstance(formatter, expected)

    @pytest.mark.parametrize(
        ("env", "expected"),
        [
            ("json", JsonFormatter),
            ("logfmt", LogfmtFormatter),
        ],
        ids=[
            "json",
            "logfmt",
        ],
    )
    def test_format_env(
        self,
        env: str,
        expected: type[AmoxFormatter],
        create_formatter: CreateFormatter,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Format resolved from AMOX_LOG_FORMAT env var."""
        monkeypatch.setenv("AMOX_LOG_FORMAT", env)
        formatter = create_formatter()
        assert isinstance(formatter, expected)


class AmoxFormatterTests:
    """
    Shared formatter behavior tests.

    Not collected directly by pytest (no `Test` prefix). Subclasses provide
    `builder` and `parser` fixtures for the specific format under test.
    """

    @pytest.fixture
    def builder(self) -> FormatterBuilder[AmoxFormatter]:
        """Protocol to define a formatter builder."""
        raise NotImplementedError

    @pytest.fixture
    def parser(self) -> LogfmtParser | JsonParser:
        """Protocol to define a parser."""
        raise NotImplementedError

    def test_default_options(
        self,
        builder: FormatterBuilder[AmoxFormatter],
        parser: LogfmtParser | JsonParser,
        record: logging.LogRecord,
    ) -> None:
        """Produces valid output with default options in expected order."""
        parsed = parser.parse_line(builder().format(record))

        assert list(parsed.keys()) == ["ts", "level", "logger", "msg"]
        assert parsed["ts"] is not None
        assert parsed["level"] == record.levelname
        assert parsed["logger"] == record.name
        assert parsed["msg"] == record.msg

    @pytest.mark.parametrize(
        ("opts", "expected"),
        [
            (FormatterOptions(include="minimal", snake_case=True), DEFAULT_KEYS_SNAKE),
            (FormatterOptions(include="minimal", snake_case=False), DEFAULT_KEYS),
            (FormatterOptions(include="verbose", snake_case=True), VERBOSE_KEYS_SNAKE),
            (FormatterOptions(include="verbose", snake_case=False), VERBOSE_KEYS),
            (FormatterOptions(include="all", snake_case=True), ALL_INCLUDE_KEYS_SNAKE),
            (FormatterOptions(include="all", snake_case=False), ALL_INCLUDE_KEYS),
            (
                FormatterOptions(include=["filename", "lineno"], snake_case=True),
                {"filename", "lineno"},
            ),
            (
                FormatterOptions(
                    include=["funcName", "lineno", "filename"],
                    snake_case=True,
                ),
                {"func_name", "lineno", "filename"},
            ),
            (
                FormatterOptions(include=["funcName", "threadName"], snake_case=False),
                {"funcName", "threadName"},
            ),
        ],
        ids=[
            "minimal_snake",
            "minimal_camel",
            "verbose_snake",
            "verbose_camel",
            "all_snake",
            "all_camel",
            "list_of_keys",
            "list_of_keys_snake",
            "list_of_keys_camel",
        ],
    )
    def test_include(
        self,
        opts: FormatterOptions,
        expected: set[str],
        builder: FormatterBuilder[AmoxFormatter],
        parser: LogfmtParser | JsonParser,
        record: logging.LogRecord,
    ) -> None:
        """The include param controls which LogRecord builtins appear in output."""
        formatter = builder(**opts)
        parsed = parser.parse_line(formatter.format(record))

        assert set(parsed.keys()) == expected

    @pytest.mark.parametrize(
        ("opts", "expected"),
        [
            (
                FormatterOptions(
                    field_remap={
                        "levelname": "severity",
                        "msg": "message",
                        "created": "timestamp",
                        "name": "source",
                    },
                    snake_case=True,
                    include="minimal",
                ),
                ["severity", "message", "timestamp", "source"],
            ),
            (
                FormatterOptions(
                    field_remap={"levelname": "lvl"},
                    snake_case=True,
                    include="minimal",
                ),
                ["lvl", "msg", "ts", "logger"],
            ),
            (
                FormatterOptions(
                    field_remap={"created": "time", "name": "service"},
                    snake_case=True,
                    include="minimal",
                ),
                ["time", "service", "level", "msg"],
            ),
            (
                FormatterOptions(
                    field_remap={"levelname": "severity"},
                    snake_case=False,
                    include="verbose",
                ),
                ["severity", "funcName", "threadName"],
            ),
            (
                FormatterOptions(
                    field_remap={"funcName": "function", "lineno": "line"},
                    snake_case=True,
                    include=["funcName", "lineno", "filename"],
                ),
                ["function", "line", "filename"],
            ),
        ],
        ids=[
            "full_remap",
            "single_key",
            "partial_remap",
            "no_snake_case",
            "explicit_list",
        ],
    )
    def test_field_remap(
        self,
        opts: FormatterOptions,
        expected: list[str],
        builder: FormatterBuilder[AmoxFormatter],
        parser: LogfmtParser | JsonParser,
        record: logging.LogRecord,
    ) -> None:
        """Custom field_remap renames output keys, respecting snake_case setting."""
        formatter = builder(**opts)
        parsed = parser.parse_line(formatter.format(record))

        assert not (set(expected) - set(parsed))

    def test_extras_appear(
        self,
        builder: FormatterBuilder[AmoxFormatter],
        parser: LogfmtParser | JsonParser,
    ) -> None:
        """Extra attributes on the record appear as top-level keys."""
        request_id = f"{uuid.uuid4()}"
        status_code = 204

        record = make_record(request_id=request_id, status_code=status_code)
        parsed = parser.parse_line(builder().format(record))

        assert parsed["request_id"] == request_id
        assert str(parsed["status_code"]) == str(status_code)

    @pytest.mark.parametrize(
        ("msg", "exc_info", "expected"),
        [
            ("failed", True, "failed"),
            ("boom", False, "boom"),
        ],
        ids=[
            "exc_info",
            "error_as_msg",
        ],
    )
    def test_exception(
        self,
        msg: str,
        exc_info: bool,
        expected: str,
        builder: FormatterBuilder[AmoxFormatter],
        parser: LogfmtParser | JsonParser,
    ) -> None:
        """
        Exception field is only emitted when exc_info is set on the record.

        The `exception` field is only emitted when `exc_info` is explicitly set on the
        LogRecord, (which exception logging level triggers).

        Reference:

            | Call (inside except block)                          | msg      | exception field  |
            | --------------------------------------------------  | -------- | ---------------- |
            | logger.error("failed")                              | "failed" | absent           |
            | logger.error(e)                                     | str(e)   | absent           |
            | logger.error("failed", exc_info=True)               | "failed" | full traceback   |
            | logger.error(e, exc_info=True)                      | str(e)   | full traceback   |
            | logger.exception("failed")                          | "failed" | full traceback   |
            | logger.error("msg", exc_info=True) *outside* except | "msg"    | "NoneType: None" |
        """  # noqa: E501
        error = ValueError("kaboom")
        info = make_exc_info(error) if exc_info else None

        record = make_record(msg=msg, level=logging.ERROR, exc_info=info)
        parsed = parser.parse_line(builder().format(record))

        assert parsed["msg"] == expected
        assert ("exception" in parsed) == exc_info


class TestLogfmtFormatter(AmoxFormatterTests):
    """Tests for `LogfmtFormatter` output and quoting behavior."""

    @t.override
    @pytest.fixture
    def builder(self) -> FormatterBuilder[LogfmtFormatter]:
        def build(**opts: t.Unpack[FormatterOptions]) -> LogfmtFormatter:
            return create_formatter("logfmt", **opts)

        return build

    @t.override
    @pytest.fixture
    def parser(self) -> LogfmtParser:
        return LogfmtParser()

    @pytest.mark.parametrize(
        ("s", "expected"),
        [
            ("", '""'),
            ("no_special", "no_special"),
            ("has spaces", '"has spaces"'),
            ("has=equals", '"has=equals"'),
            ('has"quotes', '"has\\"quotes"'),
            ("has\\backslash", '"has\\\\backslash"'),
            ('both"and\\here', '"both\\"and\\\\here"'),
            ("has\nnewline", '"has\\nnewline"'),
            ("has\ttab", '"has\\ttab"'),
        ],
        ids=[
            "empty",
            "no_quote_needed",
            "spaces",
            "equals",
            "double_quotes",
            "backslash",
            "both_quotes_and_backslash",
            "newline",
            "tab",
        ],
    )
    def test_quote(
        self,
        s: str,
        expected: str,
        builder: FormatterBuilder[LogfmtFormatter],
    ) -> None:
        """Quoting follows go-logfmt rules with backslash escaping."""
        assert builder().quote(s) == expected

    @pytest.mark.parametrize(
        "s",
        [
            "",
            "no_special",
            "has spaces",
            "has=equals",
            'has"quotes',
            "has\\backslash",
            'both"and\\here',
            "has\nnewline",
            "has\ttab",
        ],
        ids=[
            "empty",
            "no_quote_needed",
            "spaces",
            "equals",
            "double_quotes",
            "backslash",
            "both_quotes_and_backslash",
            "newline",
            "tab",
        ],
    )
    def test_quote_roundtrip(
        self,
        s: str,
        builder: FormatterBuilder[LogfmtFormatter],
        parser: LogfmtParser,
    ) -> None:
        """Quoted values round-trip through the parser without loss."""
        key = "val"
        quoted = builder().quote(s)
        parsed = parser.parse_line(f"{key}={quoted}")

        assert parsed[key] == s

    @pytest.mark.parametrize(
        ("s", "expected"),
        [
            ("simple", False),
            ("has spaces", True),
            ("has=equals", True),
            ('has"quotes', True),
            ("has\\backslash", True),
            ("has\nnewline", True),
            ("has\ttab", True),
            ("has\rcarriage", True),
            ("\x7f", True),
            ("", False),
        ],
        ids=[
            "simple",
            "spaces",
            "equals",
            "double_quotes",
            "backslash",
            "newline",
            "tab",
            "carriage_return",
            "del",
            "empty",
        ],
    )
    def test_needs_quote(
        self,
        s: str,
        expected: bool,
        builder: FormatterBuilder[LogfmtFormatter],
    ) -> None:
        """Detects values that require quoting per go-logfmt rules."""
        assert builder().needs_quote(s) == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, "null"),
            (True, "true"),
            (False, "false"),
            (42, "42"),
            (3.14, "3.14"),
        ],
        ids=["none", "true", "false", "int", "float"],
    )
    def test_encode_value_primitives(
        self,
        value: object,
        expected: str,
        builder: FormatterBuilder[LogfmtFormatter],
    ) -> None:
        """Primitive types encode without quoting."""
        assert builder().encode_value(value) == expected


class TestJsonFormatter(AmoxFormatterTests):
    """Tests for `JsonFormatter` output."""

    @t.override
    @pytest.fixture
    def builder(self) -> FormatterBuilder[JsonFormatter]:
        def build(**opts: t.Unpack[FormatterOptions]) -> JsonFormatter:
            return create_formatter("json", **opts)

        return build

    @t.override
    @pytest.fixture
    def parser(self) -> JsonParser:
        return JsonParser()
