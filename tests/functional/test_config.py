"""Functional tests for `config` API."""

import typing as t

import pytest

from tests.functional import ParsabilityScript, ParsabilityTests
from tests.functional.scripts import config


class TestConfig(ParsabilityTests):
    """Tests for `logging.config.dictConfig(config())`."""

    @t.override
    @pytest.fixture
    def parsability_script(self) -> ParsabilityScript:
        return config
