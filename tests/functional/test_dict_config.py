"""Functional tests for `dictConfig` API."""

import typing as t

import pytest

from tests.functional import ParsabilityScript, ParsabilityTests
from tests.functional.scripts import dict_config


class TestDictConfig(ParsabilityTests):
    """Tests for `logging.config.dictConfig(config())` API."""

    @t.override
    @pytest.fixture
    def parsability_script(self) -> ParsabilityScript:
        return dict_config
