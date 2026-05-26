"""
setup_name: app namespace at DEBUG, third-party INFO visible, third-party DEBUG silent.

Proves that `setup(name=...)` promotes the app logger to DEBUG while third-party loggers
inherit root's INFO level.
"""

import logging

from amox import setup

MSG = "app debug visible"
NAME = "myapp.service"
LEVEL = logging.DEBUG

THIRD_PARTY = "urllib3.connectionpool"
THIRD_PARTY_MSG = "pool is full"
THIRD_PARTY_LEVEL = logging.INFO

if __name__ == "__main__":
    setup(name="myapp")
    # app logger at DEBUG
    logging.getLogger(NAME).log(LEVEL, MSG)
    # third-party at DEBUG
    logging.getLogger(THIRD_PARTY).debug("does not appear")
    # third-party at INFO
    logging.getLogger(THIRD_PARTY).log(THIRD_PARTY_LEVEL, THIRD_PARTY_MSG)
