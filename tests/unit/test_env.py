"""Unit tests for `src.amox.env` module."""

import pytest

from amox.env import (
    LOG_FORMAT_ENV,
    LOG_LEVEL_ENV,
    resolve_bool,
    resolve_format,
    resolve_level,
)
from amox.warnings_ import AmoxConfigWarning


class TestResolveFormat:
    """Tests for `resolve_format`: reads `AMOX_LOG_FORMAT` env var."""

    @pytest.mark.parametrize(
        ("env", "expected", "warns"),
        [
            (None, "logfmt", False),
            ("logfmt", "logfmt", False),
            ("json", "json", False),
            ("JSON", "json", False),
            ("Logfmt", "logfmt", False),
            ("  json  ", "json", False),
            ("yaml", "logfmt", True),
            ("", "logfmt", True),
        ],
        ids=[
            "unset_default",
            "logfmt",
            "json",
            "json_uppercase",
            "logfmt_mixed_case",
            "json_whitespace",
            "invalid_value",
            "empty_string",
        ],
    )
    def test_resolve_format(
        self,
        env: str | None,
        expected: str,
        warns: bool,
        monkeypatch: pytest.MonkeyPatch,
        recwarn: pytest.WarningsRecorder,
    ) -> None:
        """
        Resolves format from AMOX_LOG_FORMAT environment variable.

        Invalid values fall back to the default and emit an `AmoxConfigWarning`.
        """
        if env is None:
            monkeypatch.delenv(LOG_FORMAT_ENV, raising=False)
        else:
            monkeypatch.setenv(LOG_FORMAT_ENV, env)

        result = resolve_format()

        assert result == expected

        if warns:
            assert len(recwarn) == 1
            (warn,) = recwarn
            assert warn.category is AmoxConfigWarning
        else:
            assert len(recwarn) == 0


class TestResolveLevel:
    """Tests for `resolve_level`: reads `AMOX_LOG_LEVEL` env var."""

    @pytest.mark.parametrize(
        ("env", "expected", "warns"),
        [
            (None, "WARNING", False),
            ("DEBUG", "DEBUG", False),
            ("INFO", "INFO", False),
            ("WARNING", "WARNING", False),
            ("ERROR", "ERROR", False),
            ("CRITICAL", "CRITICAL", False),
            ("NOTSET", "NOTSET", False),
            ("debug", "DEBUG", False),
            ("Info", "INFO", False),
            ("  ERROR  ", "ERROR", False),
            ("10", "DEBUG", False),
            ("20", "INFO", False),
            ("30", "WARNING", False),
            ("40", "ERROR", False),
            ("50", "CRITICAL", False),
            ("0", "NOTSET", False),
            ("VERBOSE", "WARNING", True),
            ("", "WARNING", True),
            ("99", "WARNING", True),
        ],
        ids=[
            "unset_default",
            "debug",
            "info",
            "warning",
            "error",
            "critical",
            "notset",
            "debug_lowercase",
            "info_mixed_case",
            "error_whitespace",
            "numeric_10",
            "numeric_20",
            "numeric_30",
            "numeric_40",
            "numeric_50",
            "numeric_0",
            "invalid_value",
            "empty_string",
            "numeric_invalid",
        ],
    )
    def test_resolve_level(
        self,
        env: str | None,
        expected: str,
        warns: bool,
        monkeypatch: pytest.MonkeyPatch,
        recwarn: pytest.WarningsRecorder,
    ) -> None:
        """
        Resolves level from AMOX_LOG_LEVEL environment variable.

        Invalid values fall back to the default and emit an `AmoxConfigWarning`.
        """
        if env is None:
            monkeypatch.delenv(LOG_LEVEL_ENV, raising=False)
        else:
            monkeypatch.setenv(LOG_LEVEL_ENV, env)

        result = resolve_level()

        assert result == expected

        if warns:
            assert len(recwarn) == 1
            (warn,) = recwarn
            assert warn.category is AmoxConfigWarning
        else:
            assert len(recwarn) == 0


class TestResolveBool:
    """Tests for `resolve_bool`: reads boolean env vars."""

    @pytest.mark.parametrize(
        ("env", "expected", "warns"),
        [
            (None, None, False),
            ("1", True, False),
            ("true", True, False),
            ("True", True, False),
            ("TRUE", True, False),
            ("  true  ", True, False),
            ("0", False, False),
            ("false", False, False),
            ("False", False, False),
            ("FALSE", False, False),
            ("  false  ", False, False),
            ("yes", None, True),
            ("no", None, True),
            ("on", None, True),
            ("off", None, True),
            ("2", None, True),
            ("", None, True),
        ],
        ids=[
            "unset_none",
            "truthy_1",
            "truthy_true",
            "truthy_True",
            "truthy_TRUE",
            "truthy_whitespace",
            "falsy_0",
            "falsy_false",
            "falsy_False",
            "falsy_FALSE",
            "falsy_whitespace",
            "invalid_yes",
            "invalid_no",
            "invalid_on",
            "invalid_off",
            "invalid_2",
            "empty_string",
        ],
    )
    def test_resolve_bool(
        self,
        env: str | None,
        expected: bool | None,
        warns: bool,
        monkeypatch: pytest.MonkeyPatch,
        recwarn: pytest.WarningsRecorder,
    ) -> None:
        """
        Resolves boolean from environment variable.

        Unset returns None. Invalid values emit `AmoxConfigWarning` and return None.
        """
        env_name = "TEST_BOOL_VAR"
        if env is None:
            monkeypatch.delenv(env_name, raising=False)
        else:
            monkeypatch.setenv(env_name, env)

        result = resolve_bool(env_name)

        assert result == expected

        if warns:
            assert len(recwarn) == 1
            (warn,) = recwarn
            assert warn.category is AmoxConfigWarning
        else:
            assert len(recwarn) == 0
