"""
setup_name_scope: tests that `setup(name=...)` promotes the app logger tree.

Emits an app DEBUG message (promoted by name scoping) and a third-party INFO
message. Both are visible when the test runs with `AMOX_LOG_LEVEL=INFO`.
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
