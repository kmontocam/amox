"""Schema on read parsers."""

import enum
import json
import typing as t

if t.TYPE_CHECKING:
    from amox.types_ import JsonValue


class ParseError(ValueError):
    """Raised when logfmt input is malformed."""


class LogLineParser(t.Protocol):
    """
    Protocol for structured log line parsers.

    A log line must be a single key-value mapping.
    """

    def parse_line(self, line: str) -> dict[str, object]:
        """Parse a structured log line into a dictionary."""
        ...


class LogfmtParser:
    r"""
    State machine parser for logfmt-encoded lines.

    Grammar:
        ident_byte = any byte > ' ' (0x20), excluding '=' and '"'
        key        = ident_byte { ident_byte }
        value      = ident | '"' { string_byte | '\\' any_byte } '"'
        pair       = key '=' value | key '=' | key
        message    = { garbage pair } garbage

    Reference:
        `https://github.com/go-logfmt/logfmt`
    """

    class State(enum.IntEnum):
        """Parser state machine states."""

        GARBAGE = enum.auto()
        KEY = enum.auto()
        EQUAL = enum.auto()
        IVALUE = enum.auto()
        QVALUE = enum.auto()

    def parse_line(self, line: str) -> dict[str, object]:  # noqa: C901, PLR0912, PLR0915
        r"""
        Parse a single logfmt line into a dictionary.

        Semantics follow go-logfmt:
        - bare key (no '=')    -> None
        - key=                 -> None
        - key=""               -> "" (empty string)
        - key=value            -> "value"
        - key="quoted \\"val"  -> 'quoted "val'
        """
        result: dict[str, object] = {}
        state = self.State.GARBAGE
        key = ""
        value_chars: list[str] = []
        escaped = False
        i = 0
        n = len(line)

        while i < n:
            c = line[i]

            if state == self.State.GARBAGE:
                if self.is_ident_byte(c):
                    key = c
                    state = self.State.KEY
                i += 1

            elif state == self.State.KEY:
                if c == "=":
                    state = self.State.EQUAL
                    i += 1
                elif not self.is_ident_byte(c):
                    result[key] = None
                    state = self.State.GARBAGE
                    i += 1
                else:
                    key += c
                    i += 1

            elif state == self.State.EQUAL:
                if c == '"':
                    value_chars = []
                    escaped = False
                    state = self.State.QVALUE
                    i += 1
                elif self.is_ident_byte(c):
                    value_chars = [c]
                    state = self.State.IVALUE
                    i += 1
                else:
                    result[key] = None
                    state = self.State.GARBAGE
                    i += 1

            elif state == self.State.IVALUE:
                if self.is_ident_byte(c):
                    value_chars.append(c)
                    i += 1
                else:
                    result[key] = "".join(value_chars)
                    state = self.State.GARBAGE
                    i += 1

            elif state == self.State.QVALUE:
                if escaped:
                    value_chars.append(self.unescape(c))
                    escaped = False
                    i += 1
                elif c == "\\":
                    escaped = True
                    i += 1
                elif c == '"':
                    result[key] = "".join(value_chars)
                    state = self.State.GARBAGE
                    i += 1
                else:
                    value_chars.append(c)
                    i += 1

        if state in (self.State.KEY, self.State.EQUAL):
            result[key] = None
        elif state == self.State.IVALUE:
            result[key] = "".join(value_chars)
        elif state == self.State.QVALUE:
            msg = f"unterminated quoted value for key {key!r}"
            raise ParseError(msg)

        return result

    def is_ident_byte(self, c: str) -> bool:
        """Whether a character is a valid logfmt identifier byte."""
        return c > " " and c not in {"=", '"'}

    def unescape(self, c: str) -> str:
        r"""
        Resolve a single escaped character after '\\'.

        Supports:
            \\", \\\\, \\n, \\t, \\r.

        Unknown sequences are preserved literally.
        """
        if c == '"':
            return '"'
        if c == "\\":
            return "\\"
        if c == "n":
            return "\n"
        if c == "t":
            return "\t"
        if c == "r":
            return "\r"
        return "\\" + c


class JsonParser:
    """
    Thin wrapper around `json.loads` for structured log line parsing.

    Only JSON objects (`{}`) are valid log output. Arrays, scalars, and other JSON types
    will raise `ParseError`.
    """

    def parse_line(self, line: str) -> dict[str, object]:
        """
        Parse a single JSON log line into a dictionary.

        Raises:
            `ParseError` if the line is not valid JSON
            or does not decode to a JSON object.

        """
        try:
            result: JsonValue = json.loads(line)
        except json.JSONDecodeError as e:
            msg = f"invalid json: {e}"
            raise ParseError(msg) from e
        if not isinstance(result, dict):
            msg = f"expected json object, got {type(result).__name__}"
            raise ParseError(msg)
        return result
