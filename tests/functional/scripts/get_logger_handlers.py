"""Logger with additional handlers produces formatted record on each stream."""

import logging
import sys

from amox import get_logger

MSG = "message"
NAME = "src.service"
LEVEL = logging.INFO

if __name__ == "__main__":
    handler = logging.StreamHandler(sys.stdout)
    logger = get_logger(NAME, level=LEVEL, handlers=[handler])
    logger.log(LEVEL, MSG)
