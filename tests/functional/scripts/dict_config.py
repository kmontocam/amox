"""dictConfig: configures logging via lumberjack's shipped config, produces output."""

import logging
import logging.config

from lumberjack import config

MSG: str = "configured"
NAME: str = "app.dictconfig"
LEVEL: int = logging.INFO

if __name__ == "__main__":
    logging.config.dictConfig(config())  # ty: ignore[invalid-argument-type]  # pyright: ignore[reportArgumentType]
    logger = logging.getLogger(NAME)
    logger.log(LEVEL, MSG)
