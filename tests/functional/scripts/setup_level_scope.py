"""Controls third-party log visibility with inferred level."""

import logging

from amox import setup

MSG = "information"
NAME = "third.party"
LEVEL = logging.INFO

if __name__ == "__main__":
    setup()
    logging.getLogger(NAME).log(LEVEL, MSG)
