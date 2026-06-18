"""Handlers."""

import atexit
import logging
import sys
import traceback
import typing as t
from logging.handlers import QueueHandler, QueueListener
from queue import Queue

import amox
from amox.env import DEFAULT_QUEUE, LOG_QUEUE_ENV, resolve_bool, resolve_level
from amox.formatters import QueueMixin


class LiveQueueHandler(QueueHandler):
    """
    Queue-based log handler with automatic listener lifecycle.

    The `QueueListener` is started as soon as it is attached and stopped on
    interpreter shutdown via `atexit`.
    """

    listener: QueueListener | None = None

    @t.override
    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        if name == "listener" and isinstance(value, QueueListener):
            value.start()
            _ = atexit.register(self.stop_listener)
        # forward dictConfig assignment to the listener handlers for managed formatters
        elif (
            name == "formatter"
            and self.listener
            and isinstance(value, logging.Formatter)
            and isinstance(value, QueueMixin)
            and value.forward_on_listener
        ):
            for h in self.listener.handlers:
                h.formatter = value

    def stop_listener(self) -> None:
        """
        Stop the listener if it is still running.

        Guards against double-stop when atexit fires after an explicit `listener.stop()`
        call.
        """
        if (listener := self.listener) is not None and listener._thread is not None:  # noqa: SLF001
            listener.stop()

    @t.override
    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        """
        Preserve `exc_text` for downstream formatters.

        Python 3.12's stdlib `prepare()` embeds the traceback into `record.msg`
        and clears `exc_text`, making exception info inaccessible to downstream
        formatters. Format `exc_info` into `exc_text` and only clear the tuple
        (which holds frame references and is unpicklable).

        Reference:
            `https://github.com/python/cpython/issues/107801`
        """
        if record.exc_info:
            record.exc_text = "".join(
                traceback.format_exception(*record.exc_info),
            ).rstrip("\n")
        record.exc_info = None
        return record


def create_handler(
    *,
    queue: bool | None = None,
    formatter: logging.Formatter | None = None,
    root: bool = False,
) -> logging.Handler:
    """
    Create handler based on configuration.

    Resolve the type and return the corresponding handler instance. Options include
    a raw `StreamHandler` with `sys.stderr` stream, or the same wrapped inside a
    `QueueHandler` for non blocking I/O.

    Used mainly as the factory for `dictConfig`'s `()` protocol.

    Note:
        When `root` is True, `setLevel()` is called on the root logger during
        factory invocation. Although not a formatter concern, it is embedded to provide
        a single resolution call for `dictConfig`'s dynamic configuration.

    """
    logging.root.setLevel(resolve_level()) if root else None

    stream: logging.StreamHandler[t.TextIO] = logging.StreamHandler(stream=sys.stderr)
    stream.name = amox.__name__
    stream.formatter = formatter

    use_queue = (
        queue
        if queue is not None
        else use_queue
        if (use_queue := resolve_bool(LOG_QUEUE_ENV)) is not None
        else DEFAULT_QUEUE
    )
    if not use_queue:
        return stream

    q = Queue()
    listener = QueueListener(q, stream, respect_handler_level=True)
    lqh = LiveQueueHandler(q)
    lqh.listener = listener
    return lqh


def has_handler(
    prefix: str = amox.__name__, *, logger: logging.Logger | None = None
) -> bool:
    """
    Whether any handler on the target logger is named after a given prefix.

    `dictConfig` sets `handler.name` to the dict key, so handlers installed via
    `setup()` will have names starting with the package name. Defaults to the root
    logger.
    """
    target = logger or logging.getLogger()
    return any(h.name and h.name.startswith(prefix) for h in target.handlers)
