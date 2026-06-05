# amox

Amox (from the Nahuatl _amoxtli_: book, codex, **written record**) is a zero-dependency
Python logging library to produce records on _schema-on-read_ formats.

Adheres to standard log serialization formats, including `logfmt` and `json`, with a
**single configuration line to rule a system**.

## Mental model

A service runs programmatically, emitting records for domain-specific events. Producing
messages in a human-readable format for real-time inspection is necessary, yet these
have to be processable subsequently.

Produce logs semi-structured. Let third parties do the parsing, processing or any
downstream action.

## Usage

### Initialize once

Single call, **every log record will obey the configured format**.

On application's entrypoint:

```src/main.py
from amox import setup

setup(__name__)
```

No need to modify calls to `logging.getLogger`: only ensure that loggers share the
`__name__`'s hierarchy.

```src/module/__init__.py
import logging

logger = logging.getLogger(__name__)
```

> [!NOTE]
> `amox` provides an analog to `logging`'s `getLogger` with `amox.get_logger`. However,
> usage of this function is not mandatory, it can be used interchangeably as preferred.

### Line by line

Configuration is individually possible at the logger level, yet format consistency
across all log emissions cannot be guaranteed by `amox`.

As follows

```py
import amox

logger = amox.get_logger(__name__)
```

## License

[MIT](LICENSE)
