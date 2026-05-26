"""Unit tests for `src.lumberjack.handlers` module."""

import atexit
import logging
from logging.handlers import QueueListener
from queue import SimpleQueue

import pytest

import lumberjack.handlers
from lumberjack.handlers import LiveQueueHandler
from tests.conftest import make_exc_info, make_record


class TestLiveQueueHandler:
    """Tests for `LiveQueueHandler` auto-start and prepare behavior."""

    @pytest.fixture
    def handler(self) -> LiveQueueHandler:
        """`LiveQueueHandler` handler."""
        queue: SimpleQueue[logging.LogRecord] = SimpleQueue()
        return LiveQueueHandler(queue)

    def test_listener_lifecycle(
        self,
        handler: LiveQueueHandler,
    ) -> None:
        """Assigning a QueueListener to `.listener` autostarts and stops on `stop()`."""
        handler.listener = QueueListener(handler.queue, logging.Handler())

        assert handler.listener._thread is not None  # noqa: SLF001

        handler.listener.stop()

        assert handler.listener._thread is None  # noqa: SLF001

    def test_listener_idempotent(self, handler: LiveQueueHandler) -> None:
        """Calling `stop_listener` twice does not raise (guards double-stop)."""
        handler.listener = QueueListener(handler.queue, logging.Handler())

        handler.stop_listener()
        handler.stop_listener()  # does not raise

    def test_listener_stop(self, handler: LiveQueueHandler) -> None:
        """`stop_listener` is a no-op when no listener has been assigned."""
        handler.stop_listener()  # does not raise

    def test_listener_atexit(
        self,
        handler: LiveQueueHandler,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An atexit callback is registered when a listener is assigned."""
        calls: list[object] = []
        monkeypatch.setattr(
            lumberjack.handlers.atexit,  # pyright: ignore[reportPrivateLocalImportUsage]
            atexit.register.__name__,
            calls.append,
        )

        listener = QueueListener(handler.queue, logging.Handler())
        handler.listener = listener

        assert handler.stop_listener in calls
        listener.stop()

    @pytest.mark.parametrize(
        ("exc_type", "exc_msg"),
        [
            (ValueError, "kaboom"),
            (RuntimeError, "oops"),
        ],
        ids=["value_error", "runtime_error"],
    )
    def test_prepare_preserves_exc_text(
        self,
        handler: LiveQueueHandler,
        exc_type: type[Exception],
        exc_msg: str,
    ) -> None:
        """`prepare` formats exc_info into exc_text and clears the tuple."""
        info = make_exc_info(exc_type(exc_msg))
        record = make_record(msg="failed", level=logging.ERROR, exc_info=info)

        assert record.exc_info is not None
        prepared = handler.prepare(record)

        assert prepared.exc_info is None
        assert prepared.exc_text is not None
        assert f"{exc_type.__name__}: {exc_msg}" in prepared.exc_text

    def test_prepare_without_exc_info(
        self,
        handler: LiveQueueHandler,
        record: logging.LogRecord,
    ) -> None:
        """`prepare` on a record without exc_info leaves exc_text untouched."""
        prepared = handler.prepare(record)

        assert prepared.exc_info is None
        assert prepared.exc_text is None
