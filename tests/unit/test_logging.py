"""Unit tests for `src.lumberjack.logging_` module."""

import io
import json
import logging
import logging.config
import pathlib
import types
import typing as t
from logging.handlers import QueueHandler

import jsonschema
import pytest

from lumberjack.formatters import LumberjackFormatter
from lumberjack.logging_ import (
    DEFAULT_EXISTING_LOGGER_LEVEL,
    LIB,
    config,
    get_logger,
    has_handler,
    read_config,
    setup,
)
from lumberjack.parsers import JsonParser, LogfmtParser, LogLineParser
from lumberjack.types_ import LogFormat, LogLevel

APP_LOGGER_PREFIX = "app"
OTHER_LOGGER_PREFIX = "other"
THIRD_PARTY_LOGGER = "thirdparty"


class TestConfig:
    """Tests for `config()`: get library's `logger.config.dictConfig` dictionary."""

    def test_dictconfig(self) -> None:
        """`dictConfig.json` is accepted by `logging.config.dictConfig`."""
        cfg = config()
        logging.config.dictConfig(cfg)  # ty: ignore[invalid-argument-type]  # pyright: ignore[reportArgumentType]

    def test_schema(self) -> None:
        """`dictConfig.json` conforms the managed JSON Schema for dictConfig."""
        schema_path = (
            # ../../schema/dictConfig.schema.json
            pathlib.Path(__file__).parent.parent.parent
            / "schema"
            / "dictConfig.schema.json"
        )
        # jsonschema has no typed schema param; untyped dict is fine
        schema = json.loads(schema_path.read_text())
        cfg = config()
        jsonschema.validate(cfg, schema)

    def test_deep_copy_isolation(self) -> None:
        """Mutating the returned config does not affect subsequent calls."""
        handler_name = "injected"
        a = config()
        a["handlers"][handler_name] = {"class": "logging.StreamHandler"}
        b = config()
        assert handler_name not in b["handlers"]


class TestReadConfig:
    """Tests for `read_config()`: raw JSON loading with caching."""

    def test_cache(self) -> None:
        """`read_config()` uses `functools.cache`. Same object on repeat calls."""
        a = read_config()
        b = read_config()
        assert a is b

    def teardown_method(self) -> None:
        """Clear the read_config cache to avoid cross-test pollution."""
        read_config.cache_clear()


class TestHasHandler:
    """Tests for `has_handler()`: lumberjack handler detection on root logger."""

    def test_no_handlers(self) -> None:
        """Returns False when root logger has no handlers."""
        assert has_handler() is False

    def test_lumberjack_handler(self) -> None:
        """Returns True when root has a handler named after the library."""
        handler = logging.StreamHandler()
        handler.name = f"{LIB}.queue_handler"
        logging.root.addHandler(handler)

        assert has_handler() is True

    def test_foreign_handler(self) -> None:
        """Returns False when root only has foreign-named handlers."""
        handler = logging.StreamHandler()
        handler.name = "uvicorn"
        logging.root.addHandler(handler)

        assert has_handler() is False

    def test_unnamed_handler(self) -> None:
        """Returns False when root has handlers with no name set."""
        handler = logging.StreamHandler()
        logging.root.addHandler(handler)

        assert has_handler() is False


class TestGetLogger:
    """Tests for `get_logger()`: named logger creation inline."""

    def test_named_logger(self) -> None:
        """Returns a logger with the given name."""
        name = f"{APP_LOGGER_PREFIX}.named"
        logger = get_logger(name)
        assert logger.name == name

    def test_default_level(self) -> None:
        """Default level is DEBUG so all messages pass through."""
        logger = get_logger(f"{APP_LOGGER_PREFIX}.debug")
        assert logger.level == logging.DEBUG

    def test_custom_level(self) -> None:
        """Explicit level parameter sets the logger level."""
        logger = get_logger(f"{APP_LOGGER_PREFIX}.custom", level="WARNING")
        assert logger.level == logging.WARNING

    def test_default_handler(self) -> None:
        """Attaches a `StreamHandler` with a LumberjackFormatter by default."""
        logger = get_logger(f"{APP_LOGGER_PREFIX}.handler")
        assert len(logger.handlers) == 1
        (handler,) = logger.handlers
        assert isinstance(handler, logging.StreamHandler)
        assert isinstance(handler.formatter, LumberjackFormatter)

    def test_mutate_root(self) -> None:
        """Does not add handlers to the root logger."""
        assert not logging.root.handlers
        _ = get_logger(f"{APP_LOGGER_PREFIX}.isolated")
        assert not logging.root.handlers

    def test_mutate_other_loggers(self) -> None:
        """Does not affect unrelated loggers."""
        other = logging.getLogger(f"{OTHER_LOGGER_PREFIX}.lib")
        handlers = other.handlers
        assert not handlers
        _ = get_logger(f"{APP_LOGGER_PREFIX}.only")
        assert other.handlers == handlers

    def test_handlers_untouched(self) -> None:
        """Additional handlers have no formatter attached by lumberjack."""
        handler = logging.StreamHandler(io.StringIO())
        logger = get_logger(f"{APP_LOGGER_PREFIX}.user", handlers=[handler])

        assert handler in logger.handlers
        assert handler.formatter is None

    def test_multiple_handlers(self) -> None:
        """All user-provided handlers are added alongside the default handler."""
        h1 = logging.StreamHandler(io.StringIO())
        h2 = logging.StreamHandler(io.StringIO())
        handlers: list[logging.Handler] = [h1, h2]
        logger = get_logger(f"{APP_LOGGER_PREFIX}.multi", handlers=handlers)

        assert len(logger.handlers) == len(handlers) + 1
        assert h1 in logger.handlers
        assert h2 in logger.handlers

        handler, *_ = logger.handlers
        assert isinstance(handler.formatter, LumberjackFormatter)

    def test_idempotent(self) -> None:
        """Calling twice with the same name does not duplicate handlers."""
        name = f"{APP_LOGGER_PREFIX}.idem"
        logger = get_logger(name)
        count = len(logger.handlers)
        cached_logger = get_logger(name)
        assert logger is cached_logger
        assert len(cached_logger.handlers) == count

    @pytest.mark.parametrize(
        ("log_format", "parser"),
        [
            ("logfmt", LogfmtParser()),
            ("json", JsonParser()),
        ],
        ids=["logfmt", "json"],
    )
    def test_parseable(
        self,
        log_format: LogFormat,
        parser: LogLineParser,
    ) -> None:
        """The logger produces parseable structured output for each format."""
        logger = get_logger(
            f"{APP_LOGGER_PREFIX}.output.{log_format}",
            log_format=log_format,
        )

        stream = io.StringIO()
        (handler,) = logger.handlers
        handler = t.cast("logging.StreamHandler[io.StringIO]", handler)
        handler.stream = stream

        message = "message"
        level = logging.INFO

        logger.log(level, message)
        parsed = parser.parse_line(stream.getvalue().strip())
        assert parsed["msg"] == message
        assert parsed["level"] == logging.getLevelName(level)

    @pytest.mark.parametrize(
        ("handler_name", "expects"),
        [
            (f"{LIB}.queue_handler", False),
            ("foreign", True),
        ],
        ids=[
            "lumberjack_handler",
            "foreign_handler",
        ],
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
        logger = get_logger(f"{APP_LOGGER_PREFIX}.detect.{handler_name}")

        assert bool(logger.handlers) == expects

    def teardown_method(self) -> None:
        """Clean up any loggers we created."""
        manager = logging.Logger.manager
        for name in list(manager.loggerDict.keys()):
            if name.startswith((APP_LOGGER_PREFIX, OTHER_LOGGER_PREFIX)):
                logger = logging.getLogger(name)
                logger.handlers.clear()


class TestSetup:
    """Tests for `setup()`: root logger configuration via dictConfig."""

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

    def test_queue_handler_default(self) -> None:
        """By default, `setup()` installs a `LiveQueueHandler` on root."""
        setup()

        queue_handlers = [
            h for h in logging.root.handlers if isinstance(h, QueueHandler)
        ]
        assert len(queue_handlers) == 1

    def test_queue_disabled(self) -> None:
        """`setup(queue=False)` installs a direct StreamHandler, no queue."""
        setup(queue=False)

        queue_handlers = [
            h for h in logging.root.handlers if isinstance(h, QueueHandler)
        ]
        assert len(queue_handlers) == 0
        assert len(logging.root.handlers) > 0

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

        assert (
            logging.getLogger(name).level
            == logging.getLevelNamesMapping()[DEFAULT_EXISTING_LOGGER_LEVEL]
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
        """`setup(loggers=[{"module": ..., "level": "ERROR"}])` sets explicit level."""
        setup(loggers=[{"module": reference, "level": level}])

        assert logging.getLogger(name).level == logging.getLevelNamesMapping()[level]

    def test_name_scopes(self) -> None:
        """`setup(name=...)` sets the named logger to DEBUG while root stays at INFO."""
        setup(name=APP_LOGGER_PREFIX)

        assert logging.getLogger(APP_LOGGER_PREFIX).level == logging.DEBUG
        assert logging.root.level == logging.INFO

    def teardown_method(self) -> None:
        """Clean up loggers created during tests."""
        for name in (THIRD_PARTY_LOGGER, json.__name__):
            logger = logging.getLogger(name)
            logger.handlers.clear()
            logger.setLevel(logging.NOTSET)
