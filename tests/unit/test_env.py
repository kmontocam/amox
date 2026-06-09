"""Unit tests for `src.amox.env` module."""

import pytest

from amox.env import LOG_LEVEL_ENV, resolve_level


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
            ("VERBOSE", "WARNING", True),
            ("Debug", "WARNING", True),
            ("", "WARNING", True),
        ],
        ids=[
            "unset_default",
            "debug",
            "info",
            "warning",
            "error",
            "critical",
            "notset",
            "invalid_value",
            "wrong_case",
            "empty_string",
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

        Invalid values fall back to the default and emit a UserWarning.
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
            assert warn.category is UserWarning
        else:
            assert len(recwarn) == 0
