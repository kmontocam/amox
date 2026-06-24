"""Unit tests for `src.amox.logging_` module."""

import json
import logging
import logging.config
import logging.handlers
import pathlib
import sys
import threading
import time
import types
import typing as t

import jsonschema
import pytest

import amox
from amox.env import (
    EXISTING_LEVEL_ENV,
    FORMAT_ENV,
    LEVEL_ENV,
    QUEUE_ENV,
    ROOT_LEVEL_ENV,
    resolve_level,
)
from amox.formatters import AmoxFormatter, JsonFormatter, LogfmtFormatter
from amox.handlers import LiveQueueHandler, has_handler
from amox.logging_ import (
    config,
    dict_config,
    get_logger,
    setup,
)
from amox.types_ import LogLevel
from amox.warnings_ import AmoxFormatWarning
from tests.conftest import make_record
from tests.unit.conftest import FilterCallable, GetLoggerKwargs, SupportsFilter

SRC_LOGGER_PREFIX = "src"
THIRD_PARTY_LOGGER = "thirdparty"


class TestConfig:
    """Tests for `config()`: get library's mapping for `logger.config.dictConfig`."""

    def test_dictconfig(self) -> None:
        """Settled mapping is accepted by `logging.config.dictConfig`."""
        cfg = config()
        logging.config.dictConfig(cfg)  # ty: ignore[invalid-argument-type]

    def test_schema(self) -> None:
        """Resolved configuration conforms the managed JSON Schema for `dictConfig`."""
        schema_path = (
            # ../../schema/dictConfig.json
            pathlib.Path(__file__).parent.parent.parent / "schema" / "dictConfig.json"
        )
        # jsonschema has no typed schema param; untyped dict is fine
        schema = json.loads(schema_path.read_text())
        cfg = config()
        jsonschema.validate(cfg, schema)


class TestDictConfig:
    """Tests for `dict_config()`: raw JSON loading."""

    def test_loads_config_file(self) -> None:
        """`dict_config()` loads the bundled JSON file."""
        cfg = dict_config()
        assert isinstance(cfg, dict)


class TestHasHandler:
    """Tests for `has_handler()`: amox handler detection on loggers."""

    @pytest.mark.parametrize(
        ("handler_name", "expects"),
        [
            (amox.__name__, True),
            ("foreign", False),
            (None, False),
        ],
        ids=["managed", "foreign", "unnamed"],
    )
    def test_on_root(
        self,
        handler_name: str | None,
        expects: bool,
    ) -> None:
        """Detects amox-named handlers on root logger."""
        handler = logging.Handler()
        handler.name = handler_name
        logging.root.addHandler(handler)

        assert has_handler() is expects

    @pytest.mark.parametrize(
        ("handler_name", "expects"),
        [
            (amox.__name__, True),
            ("foreign", False),
            (None, False),
        ],
        ids=["stream_handler", "foreign", "unnamed"],
    )
    def test_on_named_logger(
        self,
        handler_name: str | None,
        expects: bool,
    ) -> None:
        """Detects amox-named handlers on a named logger."""
        logger = logging.getLogger(f"{SRC_LOGGER_PREFIX}.has_handler")
        handler = logging.Handler()
        handler.name = handler_name
        logger.addHandler(handler)

        assert has_handler(logger=logger) is expects

    def teardown_method(self) -> None:
        """Clean up named logger handlers from test_on_named_logger."""
        logger = logging.getLogger(f"{SRC_LOGGER_PREFIX}.has_handler")
        logger.handlers.clear()


class TestGetLogger:
    """Tests for `get_logger()`: named logger creation inline."""

    @pytest.mark.parametrize(
        ("env", "expected"),
        [
            (None, LogfmtFormatter),
            ("logfmt", LogfmtFormatter),
            ("json", JsonFormatter),
        ],
        ids=["unset", "logfmt", "json"],
    )
    def test_format_env(
        self,
        env: str | None,
        expected: type[AmoxFormatter],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`get_logger()` honors `AMOX_FORMAT` env var."""
        if env is None:
            monkeypatch.delenv(FORMAT_ENV, raising=False)
        else:
            monkeypatch.setenv(FORMAT_ENV, env)

        # disable queue for direct formatter access
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.format_env", queue=False)
        assert len(logger.handlers) == 1
        (handler,) = logger.handlers
        assert isinstance(handler.formatter, expected)

    @pytest.mark.parametrize(
        ("env", "expected"),
        [
            (None, LiveQueueHandler),
            ("true", LiveQueueHandler),
            ("false", logging.StreamHandler),
        ],
        ids=["unset", "queue", "stream"],
    )
    def test_queue_env(
        self,
        env: str | None,
        expected: type[logging.Handler],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`get_logger()` honors `AMOX_QUEUE` env var."""
        if env is None:
            monkeypatch.delenv(QUEUE_ENV, raising=False)
        else:
            monkeypatch.setenv(QUEUE_ENV, env)

        logger = get_logger(f"{SRC_LOGGER_PREFIX}.queue_env")
        assert len(logger.handlers) == 1
        (handler,) = logger.handlers
        assert isinstance(handler, expected)

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            (f"{SRC_LOGGER_PREFIX}.named", f"{SRC_LOGGER_PREFIX}.named"),
            (None, "root"),
        ],
        ids=["named", "root"],
    )
    def test_logger_name(self, name: str | None, expected: str) -> None:
        """Returns a logger with the expected name."""
        logger = get_logger(name)
        assert logger.name == expected

    def test_default_level(self) -> None:
        """Default level follows `AMOX_LEVEL` env var (DEBUG by default)."""
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.debug")
        log_levels_map = logging.getLevelNamesMapping()
        assert logger.level == log_levels_map[resolve_level(LEVEL_ENV)]

    def test_custom_level(self) -> None:
        """Explicit level parameter sets the logger level."""
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.custom", level="WARNING")
        assert logger.level == logging.WARNING

    def test_handler_name(self) -> None:
        """StreamHandler is named with the library prefix."""
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.handler_name")
        (handler,) = logger.handlers
        assert handler.name == amox.__name__

    @pytest.mark.parametrize(
        ("queue", "expected"),
        [
            (True, LiveQueueHandler),
            (False, logging.StreamHandler),
        ],
        ids=["queue", "stream"],
    )
    def test_default_handler(
        self,
        queue: bool,
        expected: type[logging.Handler],
    ) -> None:
        """Attaches handler with an AmoxFormatter by default."""
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.handler", queue=queue)
        assert len(logger.handlers) == 1
        (handler,) = logger.handlers
        assert isinstance(handler, expected)
        if isinstance(handler, LiveQueueHandler) and (listener := handler.listener):
            assert len(listener.handlers) == 1
            (handler,) = listener.handlers
        assert isinstance(handler.formatter, AmoxFormatter)

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            (f"{SRC_LOGGER_PREFIX}.propagate", False),
            (None, True),
        ],
        ids=["named", "root"],
    )
    def test_propagate(self, name: str | None, expected: bool) -> None:
        """Named loggers have propagation disabled; root stays enabled."""
        logger = get_logger(name)
        assert logger.propagate is expected

    def test_mutate_root(self) -> None:
        """Does not add handlers to the root logger when given a name."""
        assert not logging.root.handlers
        _ = get_logger(f"{SRC_LOGGER_PREFIX}.isolated")
        assert not logging.root.handlers

    def test_mutate_other_loggers(self) -> None:
        """Does not affect unrelated loggers."""
        other = logging.getLogger(f"{THIRD_PARTY_LOGGER}.lib")
        handlers = other.handlers
        assert not handlers
        _ = get_logger(f"{SRC_LOGGER_PREFIX}.only")
        assert other.handlers == handlers

    @pytest.mark.parametrize(
        ("queue", "expected"),
        [
            (True, 1),
            (False, 2),
        ],
        ids=["queue", "stream"],
    )
    def test_handlers(
        self,
        queue: bool,
        expected: int,
    ) -> None:
        """Additional handlers are included and have formatter attached by amox."""
        stream = logging.StreamHandler(sys.stderr)
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.user", queue=queue, handlers=[stream])
        assert len(logger.handlers) == expected
        (handler, *_) = logger.handlers
        container: logging.Logger | logging.handlers.QueueListener = logger
        if isinstance(handler, LiveQueueHandler) and (listener := handler.listener):
            *_, stream = listener.handlers
            container = listener

        assert stream in container.handlers
        assert isinstance(stream.formatter, AmoxFormatter)

    def test_idempotent(self) -> None:
        """Calling twice with the same name does not duplicate handlers."""
        name = f"{SRC_LOGGER_PREFIX}.idem"
        logger = get_logger(name)
        count = len(logger.handlers)
        cached_logger = get_logger(name)
        assert logger is cached_logger
        assert len(cached_logger.handlers) == count

    @pytest.mark.parametrize(
        ("kwargs", "expects"),
        [
            (GetLoggerKwargs(log_format="json"), True),
            (GetLoggerKwargs(snake_case=True), True),
            (GetLoggerKwargs(level="WARNING"), True),
            (GetLoggerKwargs(handlers=[]), False),
            (GetLoggerKwargs(queue=True), True),
        ],
        ids=["format", "opts", "level", "handlers", "queue"],
    )
    def test_configured_warning(
        self,
        kwargs: GetLoggerKwargs,
        expects: bool,
        recwarn: pytest.WarningsRecorder,
    ) -> None:
        """
        Repeat calls on a get_logger-configured logger warn on any keyword arguments.

        Once `get_logger` owns a logger, all configuration is final.
        """
        name = f"{SRC_LOGGER_PREFIX}.configured_warn"
        _ = get_logger(name)
        _ = get_logger(name, **kwargs)

        if expects:
            (warn,) = recwarn
            assert warn.category is AmoxFormatWarning
        else:
            assert not recwarn.list

    @pytest.mark.parametrize(
        ("kwargs", "expects"),
        [
            (GetLoggerKwargs(log_format="json"), True),
            (GetLoggerKwargs(level="WARNING"), False),
        ],
        ids=["format", "level"],
    )
    def test_setup_warning(
        self,
        kwargs: GetLoggerKwargs,
        expects: bool,
        recwarn: pytest.WarningsRecorder,
    ) -> None:
        """After `setup()`, calls warn only when formatting options are passed."""
        setup()
        _ = get_logger(f"{SRC_LOGGER_PREFIX}.setup_warn", **kwargs)

        if expects:
            (warn,) = recwarn
            assert warn.category is AmoxFormatWarning
        else:
            assert not recwarn.list

    @pytest.mark.parametrize(
        ("handler_name", "expects"),
        [
            (amox.__name__, False),
            ("foreign", True),
        ],
        ids=["managed_handler", "foreign_handler"],
    )
    def test_setup_early_exit(
        self,
        handler_name: str,
        expects: bool,
    ) -> None:
        """
        `get_logger` skips adding its handler when root already has a managed handler.

        Foreign handlers do not trigger the skip.
        """
        handler = logging.StreamHandler()
        handler.name = handler_name
        logging.root.addHandler(handler)
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.detect.{handler_name}")

        assert bool(logger.handlers) == expects

    def test_setup_level(self) -> None:
        """After `setup()`, `get_logger()` still sets the level."""
        setup()
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.setup_active.level", level="WARNING")
        assert logger.level == logging.WARNING

    def test_setup_no_handler(self) -> None:
        """After `setup()`, `get_logger()` adds no handler on the named logger."""
        setup(name=f"{SRC_LOGGER_PREFIX}.setup_active")
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.setup_active.no_handler")
        assert not logger.handlers

    @pytest.mark.parametrize(
        ("queue"),
        [True, False],
        ids=["queue", "stream"],
    )
    def test_setup_handler(
        self,
        queue: bool,
    ) -> None:
        """After `setup(queue=)`, user-provided handlers are added."""
        setup(queue=queue)
        h = logging.Handler()
        name = f"{SRC_LOGGER_PREFIX}.setup_active.handlers"
        logger = get_logger(name, handlers=[h])

        # on queue: giving handlers are expected to escalate all the way to the root's
        # queue to produce non-blocking I/O, with a filterer with name.
        if queue and (
            (handler := logging.root.handlers[0])
            and isinstance(handler, LiveQueueHandler)
            and (listener := handler.listener)
        ):
            assert h in listener.handlers
            assert h.filters
            assert isinstance(h.formatter, AmoxFormatter)

        else:
            assert h in logger.handlers

    def test_setup_handler_placement(self) -> None:
        """After setup(queue=True), extra handler is in listener, not in logger."""
        setup(queue=True)
        h = logging.Handler()
        name = f"{SRC_LOGGER_PREFIX}.placement"
        logger = get_logger(name, handlers=[h])

        assert h not in logger.handlers
        (handler,) = logging.root.handlers
        assert isinstance(handler, LiveQueueHandler)
        listener = handler.listener
        assert listener is not None
        assert h in listener.handlers

    def test_setup_handler_filter(self) -> None:
        """After setup(queue=True), extra handler filter only passes matching name."""
        setup(queue=True)
        h = logging.Handler()
        name = f"{SRC_LOGGER_PREFIX}.filter_test"
        # handler propagates to root's queue and filter by name.
        _ = get_logger(name, handlers=[h])

        assert len(h.filters) == 1
        (filterer,) = h.filters

        matching = make_record(name=name)
        other = make_record(name="other.logger")

        assert self.is_filter_callable(filterer)

        assert filterer(matching) is True
        assert filterer(other) is False

    def test_setup_handler_queue_emission(self) -> None:
        """After setup(queue=True), additional handlers records flow through queue."""
        setup(queue=True)
        thread: threading.Thread | None = None
        event = threading.Event()

        class RecordingHandler(logging.Handler):
            """Capture thread activity inside handler."""

            @t.override
            def emit(self, record: logging.LogRecord) -> None:
                nonlocal thread
                thread = threading.current_thread()
                event.set()

        h = RecordingHandler()
        name = f"{SRC_LOGGER_PREFIX}.emission"
        logger = get_logger(name, handlers=[h])

        main_thread = threading.current_thread()

        self.drop_root_default_stream()

        logger.info("test message")

        assert event.wait(timeout=2.0)
        assert thread != main_thread

    def test_setup_handler_queue_nonblocking(self) -> None:
        """After setup(queue=True), handlers do not block I/O."""
        setup(queue=True)
        records: list[logging.LogRecord] = []
        event = threading.Event()
        throttle = 0.04
        n = 4

        class BlockingHandler(logging.Handler):
            """Blocking I/O handler."""

            @t.override
            def emit(self, record: logging.LogRecord) -> None:
                time.sleep(throttle)
                records.append(record)
                if len(records) == n:
                    event.set()

        h = BlockingHandler()
        name = f"{SRC_LOGGER_PREFIX}.nonblocking"
        logger = get_logger(name, handlers=[h])

        self.drop_root_default_stream()

        # handler takes (n * throttle) to emit all records, yet logging
        # must not block I/O
        for i in range(n):
            message = f"tick: {i}"
            logger.info(message)

        # blocking handler has not managed to emit any record
        assert len(records) == 0
        assert event.wait(timeout=n + 1 * throttle)
        assert len(records) == n

    def is_filter_callable(
        self, obj: logging.Filter | FilterCallable | SupportsFilter
    ) -> t.TypeGuard[FilterCallable]:
        """Guard lambda filter used in `get_logger()` for additional handlers."""
        return callable(obj)

    def drop_root_default_stream(self) -> logging.handlers.QueueListener:
        """Remove the default stream handler from the root queue listener."""
        assert len(logging.root.handlers) == 1
        (handler,) = logging.root.handlers
        assert isinstance(handler, LiveQueueHandler)
        listener = handler.listener
        assert listener is not None
        handlers = [lh for lh in listener.handlers if lh.name != amox.__name__]
        listener.handlers = tuple(handlers)
        return listener

    def teardown_method(self) -> None:
        """Clean up any loggers we created."""
        manager = logging.Logger.manager
        for name in list(manager.loggerDict.keys()):
            if name.startswith((SRC_LOGGER_PREFIX, THIRD_PARTY_LOGGER)):
                logger = logging.getLogger(name)
                logger.handlers.clear()
                logger.propagate = True
                logger.setLevel(logging.NOTSET)


class TestSetup:
    """Tests for `setup()`: root logger configuration via dictConfig."""

    @pytest.mark.parametrize(
        ("env", "expected"),
        [
            (None, logging.DEBUG),
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
        ],
        ids=["unset", "debug", "info"],
    )
    def test_namespace_level_env(
        self,
        env: str | None,
        expected: int,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`setup(name=...)` honors `AMOX_LEVEL` env var."""
        if env is None:
            monkeypatch.delenv(LEVEL_ENV, raising=False)
        else:
            monkeypatch.setenv(LEVEL_ENV, env)

        setup(name=SRC_LOGGER_PREFIX)

        assert logging.getLogger(SRC_LOGGER_PREFIX).level == expected

    @pytest.mark.parametrize(
        ("env", "expected"),
        [
            (None, logging.WARNING),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
        ],
        ids=["unset", "warning", "error"],
    )
    def test_existing_level_env(
        self,
        env: str | None,
        expected: int,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`setup(loggers=[...])` honors `AMOX_EXISTING_LEVEL` env var."""
        if env is None:
            monkeypatch.delenv(EXISTING_LEVEL_ENV, raising=False)
        else:
            monkeypatch.setenv(EXISTING_LEVEL_ENV, env)

        setup(loggers=[THIRD_PARTY_LOGGER])

        assert logging.getLogger(THIRD_PARTY_LOGGER).level == expected

    @pytest.mark.parametrize(
        ("env", "expected"),
        [
            (None, LiveQueueHandler),
            ("true", LiveQueueHandler),
            ("false", logging.StreamHandler),
        ],
        ids=["unset_default", "queue", "stream"],
    )
    def test_queue_env(
        self,
        env: str | None,
        expected: type[logging.Handler],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`setup()` honors `AMOX_QUEUE` env var."""
        if env is None:
            monkeypatch.delenv(QUEUE_ENV, raising=False)
        else:
            monkeypatch.setenv(QUEUE_ENV, env)

        setup()

        assert len(logging.root.handlers) == 1
        (handler,) = logging.root.handlers
        assert isinstance(handler, expected)

    def test_installs_handler(self) -> None:
        """`setup()` installs a handler on the root logger."""
        setup()

        assert len(logging.root.handlers) > 0
        assert has_handler()

    def test_idempotent(self) -> None:
        """Calling `setup()` twice does not duplicate handlers."""
        setup()
        count = len(logging.root.handlers)
        setup()

        assert len(logging.root.handlers) == count

    def test_handler_default(self) -> None:
        """By default, `setup()` installs a `LiveQueueHandler` on root."""
        setup()

        handlers = logging.root.handlers
        assert len(handlers) == 1
        (handler,) = handlers
        assert isinstance(handler, LiveQueueHandler)

    def test_queue_disabled(self) -> None:
        """queue=False installs a direct StreamHandler, no queue."""
        setup(queue=False)

        handlers = logging.root.handlers
        assert len(handlers) == 1
        (handler,) = handlers
        assert isinstance(handler, logging.StreamHandler)

    @pytest.mark.parametrize(
        ("reference", "name"),
        [
            (THIRD_PARTY_LOGGER, THIRD_PARTY_LOGGER),
            (json, json.__name__),
        ],
        ids=["string", "module"],
    )
    def test_loggers_default(
        self,
        reference: str | types.ModuleType,
        name: str,
    ) -> None:
        """`setup(loggers=[...])` sets the named logger to default level."""
        setup(loggers=[reference])

        log_levels_map = logging.getLevelNamesMapping()
        assert (
            logging.getLogger(name).level
            == log_levels_map[resolve_level(EXISTING_LEVEL_ENV)]
        )

    @pytest.mark.parametrize(
        ("reference", "name", "level"),
        [
            (THIRD_PARTY_LOGGER, THIRD_PARTY_LOGGER, "ERROR"),
            (json, json.__name__, "INFO"),
        ],
        ids=["string", "module"],
    )
    def test_loggers_with_level(
        self,
        reference: str | types.ModuleType,
        name: str,
        level: LogLevel,
    ) -> None:
        """loggers=[{"module": ..., "level": "ERROR"}] sets explicit level."""
        setup(loggers=[{"module": reference, "level": level}])

        log_levels_map = logging.getLevelNamesMapping()
        assert logging.getLogger(name).level == log_levels_map[level]

    def test_name_scopes(self) -> None:
        """name=... sets logger to `AMOX_LEVEL`, root to `AMOX_ROOT_LEVEL`."""
        setup(name=SRC_LOGGER_PREFIX)

        log_levels_map = logging.getLevelNamesMapping()
        assert (
            logging.getLogger(SRC_LOGGER_PREFIX).level
            == log_levels_map[resolve_level(LEVEL_ENV)]
        )
        assert logging.root.level == log_levels_map[resolve_level(ROOT_LEVEL_ENV)]

    def test_removes_get_logger_handlers(self) -> None:
        """Removes handlers from `get_logger`-configured loggers."""
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.removal")
        assert has_handler(logger=logger)

        setup()

        assert not has_handler(logger=logger)
        assert logger.propagate is True

    def teardown_method(self) -> None:
        """Clean up loggers created during tests."""
        for name in (THIRD_PARTY_LOGGER, json.__name__):
            logger = logging.getLogger(name)
            logger.handlers.clear()
            logger.setLevel(logging.NOTSET)
