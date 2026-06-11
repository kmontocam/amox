"""Configures logging inline via resolved config, produces a single log line."""

import logging
import logging.config

from amox import config

MSG: str = "configured"
NAME: str = "src.dictconfig"
LEVEL: int = logging.INFO

if __name__ == "__main__":
    logging.config.dictConfig(config())  # ty: ignore[invalid-argument-type]
    logger = logging.getLogger(NAME)
    logger.log(LEVEL, MSG)
