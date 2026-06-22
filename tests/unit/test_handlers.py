"""Unit tests for `src.amox.handlers` module."""

import atexit
import logging
from logging.handlers import QueueListener
from queue import SimpleQueue

import pytest

import amox.handlers
from amox.env import LOG_LEVEL_ENV, LOG_QUEUE_ENV
from amox.formatters import LogfmtFormatter
from amox.handlers import LiveQueueHandler, create_handler
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
            amox.handlers.atexit,
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


class TestCreateHandler:
    """Tests for the `create_handler` factory function."""

    def test_default(
        self,
    ) -> None:
        """Default behavior creates a LiveQueueHandler."""
        handler = create_handler()

        assert isinstance(handler, LiveQueueHandler)
        handler.stop_listener()

    def test_non_queue(self) -> None:
        """queue=False returns a plain StreamHandler."""
        handler = create_handler(queue=False)

        assert isinstance(handler, logging.StreamHandler)

    @pytest.mark.parametrize(
        ("env", "expected"),
        [
            ("false", logging.StreamHandler),
            ("true", LiveQueueHandler),
        ],
        ids=[
            "env_false_stream",
            "env_true_queue",
        ],
    )
    def test_queue_env(
        self,
        env: str,
        expected: type[logging.Handler],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """No queue defers to `AMOX_QUEUE` env var."""
        monkeypatch.setenv(LOG_QUEUE_ENV, env)
        handler = create_handler()

        assert isinstance(handler, expected)
        if isinstance(handler, LiveQueueHandler):
            handler.stop_listener()

    def test_queue_overrides_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Explicit queue parameter overrides `AMOX_QUEUE` env var."""
        monkeypatch.setenv(LOG_QUEUE_ENV, "true")
        handler = create_handler(queue=False)

        assert isinstance(handler, logging.StreamHandler)

    @pytest.mark.parametrize(
        ("env", "expected"),
        [
            ("INFO", logging.INFO),
            ("ERROR", logging.ERROR),
            ("DEBUG", logging.DEBUG),
        ],
        ids=[
            "info",
            "error",
            "debug",
        ],
    )
    def test_root(
        self,
        env: str,
        expected: int,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """root=True sets the root logger level from env var."""
        monkeypatch.setenv(LOG_LEVEL_ENV, env)

        handler = create_handler(root=True)

        assert logging.root.level == expected
        if isinstance(handler, LiveQueueHandler):
            handler.stop_listener()

    def test_root_no_side_effect(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """root=False does not modify the root logger level."""
        monkeypatch.setenv(LOG_LEVEL_ENV, "INFO")
        logging.root.setLevel(logging.WARNING)

        handler = create_handler(root=False)

        assert logging.root.level == logging.WARNING
        if isinstance(handler, LiveQueueHandler):
            handler.stop_listener()

    def test_queue_inner_formatter(self) -> None:
        """Formatter parameter is attached to the inner StreamHandler."""
        formatter = LogfmtFormatter()
        handler = create_handler(queue=True, formatter=formatter)

        assert isinstance(handler, LiveQueueHandler)
        assert handler.listener is not None
        inner_handlers = handler.listener.handlers
        assert len(inner_handlers) == 1
        (inner_handler,) = inner_handlers
        assert inner_handler.formatter is formatter
        handler.stop_listener()

    def test_stream_formatter(self) -> None:
        """Formatter is attached directly when queue=False."""
        formatter = LogfmtFormatter()
        handler = create_handler(queue=False, formatter=formatter)

        assert isinstance(handler, logging.StreamHandler)
        assert handler.formatter is formatter
