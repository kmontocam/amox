"""Handlers."""

import atexit
import logging
import traceback
import typing as t
from logging.handlers import QueueHandler, QueueListener


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
