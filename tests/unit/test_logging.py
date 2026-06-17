"""Unit tests for `src.amox.logging_` module."""

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

import amox
from amox.formatters import AmoxFormatter
from amox.logging_ import (
    DEFAULT_EXISTING_LOGGER_LEVEL,
    config,
    dict_config,
    get_logger,
    has_handler,
    setup,
)
from amox.parsers import JsonParser, LogfmtParser, LogLineParser
from amox.types_ import FormatterOptions, LogFormat, LogLevel
from amox.warnings_ import AmoxFormatWarning

SRC_LOGGER_PREFIX = "src"
THIRD_PARTY_LOGGER = "thirdparty"


class GetLoggerKwargs(FormatterOptions, total=False):
    """Keyword arguments for `get_logger()` in parametrized tests."""

    level: LogLevel | int
    log_format: LogFormat | None
    handlers: list[logging.Handler]


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
        handler = logging.StreamHandler()
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
        handler = logging.StreamHandler()
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
        """Default level is DEBUG so all messages pass through."""
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.debug")
        assert logger.level == logging.DEBUG

    def test_custom_level(self) -> None:
        """Explicit level parameter sets the logger level."""
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.custom", level="WARNING")
        assert logger.level == logging.WARNING

    def test_handler_name(self) -> None:
        """StreamHandler is named with the library prefix."""
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.handler_name")
        (handler,) = logger.handlers
        assert handler.name == amox.__name__

    def test_default_handler(self) -> None:
        """Attaches a StreamHandler with an AmoxFormatter by default."""
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.handler")
        assert len(logger.handlers) == 1
        (handler,) = logger.handlers
        assert isinstance(handler, logging.StreamHandler)
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

    def test_handlers_formatter(self) -> None:
        """Additional handlers have formatter attached by amox."""
        handler = logging.StreamHandler(io.StringIO())
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.user", handlers=[handler])

        assert handler in logger.handlers
        assert isinstance(handler.formatter, AmoxFormatter)

    def test_multiple_handlers(self) -> None:
        """All user-provided handlers are added alongside the default handler."""
        h1 = logging.StreamHandler(io.StringIO())
        h2 = logging.StreamHandler(io.StringIO())
        handlers: list[logging.Handler] = [h1, h2]
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.multi", handlers=handlers)

        assert len(logger.handlers) == len(handlers) + 1
        assert h1 in logger.handlers
        assert h2 in logger.handlers

        handler, *_ = logger.handlers
        assert isinstance(handler.formatter, AmoxFormatter)

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
            ({"log_format": "json"}, True),
            ({"snake_case": False}, True),
            ({"level": "WARNING"}, True),
            ({"handlers": []}, True),
        ],
        ids=["format", "opts", "level", "handlers"],
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
            ({"log_format": "json"}, True),
            ({"level": "WARNING"}, False),
        ],
        ids=["format", "level"],
    )
    def test_setup_active_warning(
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
            f"{SRC_LOGGER_PREFIX}.output.{log_format}",
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

    def test_setup_active_no_handler(self) -> None:
        """After `setup()`, `get_logger()` adds no handler on the named logger."""
        setup(name=f"{SRC_LOGGER_PREFIX}.setup_active")
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.setup_active.no_handler")
        assert not logger.handlers

    def test_setup_active_level(self) -> None:
        """After `setup()`, `get_logger()` still sets the level."""
        setup()
        logger = get_logger(f"{SRC_LOGGER_PREFIX}.setup_active.level", level="WARNING")
        assert logger.level == logging.WARNING

    def test_setup_active_handlers(self) -> None:
        """After `setup()`, user-provided handlers are still added."""
        setup()
        handler = logging.StreamHandler(io.StringIO())
        logger = get_logger(
            f"{SRC_LOGGER_PREFIX}.setup_active.handlers", handlers=[handler]
        )
        assert handler in logger.handlers

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
        """queue=False installs a direct StreamHandler, no queue."""
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
        """loggers=[{"module": ..., "level": "ERROR"}] sets explicit level."""
        setup(loggers=[{"module": reference, "level": level}])

        assert logging.getLogger(name).level == logging.getLevelNamesMapping()[level]

    def test_name_scopes(self) -> None:
        """name=... sets named logger to DEBUG, root stays at WARNING."""
        setup(name=SRC_LOGGER_PREFIX)

        assert logging.getLogger(SRC_LOGGER_PREFIX).level == logging.DEBUG
        assert logging.root.level == logging.WARNING

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
