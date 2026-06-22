"""Produces a single log line from on demand logger."""

import logging

from amox import get_logger

MSG: str = "message"
NAME: str = "src.service"
LEVEL: int = logging.INFO

if __name__ == "__main__":
    logger = get_logger(NAME, level=LEVEL)
    logger.info(MSG)
