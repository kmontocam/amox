"""get_logger: produces a single structured log line."""

import logging

from amox import get_logger

MSG: str = "hello"
NAME: str = "app.service"
LEVEL: int = logging.INFO

if __name__ == "__main__":
    logger = get_logger(NAME, level=LEVEL)
    logger.info(MSG)
