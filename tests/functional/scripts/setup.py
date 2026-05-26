"""
setup: configures root logger, produces a single structured log line.

Also emits a third-party DEBUG that is suppressed by root's INFO level.
"""

import logging

from amox import setup

MSG: str = "started"
NAME: str = "app.worker"
LEVEL: int = logging.INFO

if __name__ == "__main__":
    setup()
    logger = logging.getLogger(NAME)
    logger.log(LEVEL, MSG)
    # third-party DEBUG, suppressed by root INFO
    logging.getLogger("urllib3.connectionpool").debug("does not appear")
