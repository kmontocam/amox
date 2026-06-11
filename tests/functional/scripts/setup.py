"""Sets up logging, produces a single log line."""

import logging

from amox import setup

MSG: str = "started"
NAME: str = "src"
LEVEL: int = logging.INFO

THIRD_PARTY = "third.party"
THIRD_PARTY_MSG = "information"

if __name__ == "__main__":
    setup()
    logger = logging.getLogger(NAME)
    logger.log(LEVEL, MSG)
    # third-party DEBUG: suppressed resolved config's root logging level
    logging.getLogger(THIRD_PARTY).debug(THIRD_PARTY_MSG)
