"""Functional tests for `get_logger` API."""

import typing as t

import pytest

from tests.functional import ParsabilityScript, ParsabilityTests
from tests.functional.scripts import get_logger


class TestGetLogger(ParsabilityTests):
    """Tests for `get_logger()` API."""

    @t.override
    @pytest.fixture
    def parsability_script(self) -> ParsabilityScript:
        return get_logger
