"""Unit test configuration."""

import logging
from collections import abc

import pytest


@pytest.fixture(autouse=True)
def isolate_root_logger() -> abc.Generator[None]:
    """
    Clear root logger handlers before each test and restore after.

    Prevents test pollution from `setup()` calls or leftover handlers.
    """
    saved = logging.root.handlers[:]
    logging.root.handlers.clear()
    yield
    logging.root.handlers[:] = saved
