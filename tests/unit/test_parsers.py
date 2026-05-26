"""Unit tests for `src.lumberjack.parsers` module."""

import pytest

from lumberjack.parsers import JsonParser, LogfmtParser, ParseError


class TestLogfmtParser:
    """Tests for `LogfmtParser`."""

    @pytest.fixture
    def parser(self) -> LogfmtParser:
        """Logfmt parser."""
        return LogfmtParser()

    def test_unterminated_quote_raises(self, parser: LogfmtParser) -> None:
        """Unterminated quoted value raises `ParseError`."""
        with pytest.raises(ParseError):
            _ = parser.parse_line('key="no closing quote')

    @pytest.mark.parametrize(
        ("c", "expected"),
        [
            ("a", True),
            ("Z", True),
            ("0", True),
            ("_", True),
            (" ", False),
            ("=", False),
            ('"', False),
            ("\t", False),
            ("\x00", False),
        ],
        ids=[
            "lowercase",
            "uppercase",
            "digit",
            "underscore",
            "space",
            "equals",
            "double_quote",
            "tab",
            "null",
        ],
    )
    def test_ident_byte(
        self,
        parser: LogfmtParser,
        c: str,
        expected: bool,
    ) -> None:
        """Identifier bytes are any char > ' ' excluding '=' and '"'."""
        assert parser.is_ident_byte(c) == expected

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("", {}),
            ("   \t  ", {}),
            ("key=value", {"key": "value"}),
            ("level=INFO msg=hello", {"level": "INFO", "msg": "hello"}),
            (
                'ts=1970-01-01T00:00:00Z level=ERROR msg="something broke"',
                {
                    "ts": "1970-01-01T00:00:00Z",
                    "level": "ERROR",
                    "msg": "something broke",
                },
            ),
            ("key", {"key": None}),
            ("key=", {"key": None}),
            ('key=""', {"key": ""}),
            ('key="quoted"', {"key": "quoted"}),
            (r'k="hello \"world\""', {"k": 'hello "world"'}),
            (r'k="back\\slash"', {"k": "back\\slash"}),
            (r'k="new\nline"', {"k": "new\nline"}),
            (r'k="tab\there"', {"k": "tab\there"}),
            (r'k="cr\rhere"', {"k": "cr\rhere"}),
            (r'k="unknown\x"', {"k": "unknown\\x"}),
        ],
        ids=[
            "empty_line",
            "whitespace_only",
            "single_pair",
            "multiple_pairs",
            "mixed_quoted_and_bare",
            "bare_key",
            "key_equals_no_value",
            "key_equals_empty_quoted",
            "key_equals_quoted_value",
            "escaped_quote",
            "escaped_backslash",
            "escaped_newline",
            "escaped_tab",
            "escaped_carriage_return",
            "unknown_escape_preserved",
        ],
    )
    def test_parse_line(
        self,
        parser: LogfmtParser,
        line: str,
        expected: dict[str, str | None],
    ) -> None:
        """
        Parses well-formed logfmt lines into key-value dictionaries.

        Value assignment semantics per go-logfmt grammar:

        - empty / whitespace   -> {}
        - bare key (no '=')    -> None
        - key=                 -> None
        - key=""               -> "" (empty string)
        - key=value            -> "value"
        - key="quoted"         -> "quoted" (with escape resolution)
        """
        assert parser.parse_line(line) == expected


class TestJsonParser:
    """Tests for `JsonParser` wrapper."""

    @pytest.fixture
    def parser(self) -> JsonParser:
        """Json parser."""
        return JsonParser()

    def test_invalid_json_raises(self, parser: JsonParser) -> None:
        """Malformed JSON raises `ParseError`."""
        with pytest.raises(ParseError):
            _ = parser.parse_line("{not valid json")

    @pytest.mark.parametrize(
        "line",
        [
            "[1, 2, 3]",
            '"just a string"',
            "42",
            "true",
            "null",
        ],
        ids=[
            "array",
            "string",
            "number",
            "boolean",
            "null",
        ],
    )
    def test_non_object_raises(self, parser: JsonParser, line: str) -> None:
        """Valid JSON that is not an object raises `ParseError`."""
        with pytest.raises(ParseError):
            _ = parser.parse_line(line)

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("{}", {}),
            (
                '{"level": "INFO", "msg": "hello", "count": 42}',
                {"level": "INFO", "msg": "hello", "count": 42},
            ),
            (
                '{"ctx": {"request_id": "abc"}}',
                {"ctx": {"request_id": "abc"}},
            ),
        ],
        ids=[
            "empty_object",
            "flat_object",
            "nested_object",
        ],
    )
    def test_parse_line(
        self,
        parser: JsonParser,
        line: str,
        expected: dict[str, object],
    ) -> None:
        """Valid JSON objects parse into dictionaries, including nested structures."""
        assert parser.parse_line(line) == expected
