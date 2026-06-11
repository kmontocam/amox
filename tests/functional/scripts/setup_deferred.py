"""Defer logging setup."""

import logging

from amox import get_logger, setup

MSG = "after setup"
NAME = "src.before_setup"
LEVEL: int = logging.INFO

if __name__ == "__main__":
    # creation of logger prior to `setup()`, assigned format must be ignored
    logger = get_logger(NAME, log_format="json")
    setup()
    logger.log(LEVEL, MSG)
