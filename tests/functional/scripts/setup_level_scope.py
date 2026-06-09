"""
setup_level_scope: tests that root level controls third-party log visibility.

Emits an app DEBUG message (promoted by `setup(name=...)`) and a third-party
INFO message. With WARNING root, only the app message is visible; with INFO
root, both are visible.
"""

import logging

from amox import setup

MSG = "app debug visible"
NAME = "myapp.levelscope"
LEVEL = logging.DEBUG

THIRD_PARTY = "urllib3.connectionpool"
THIRD_PARTY_MSG = "third-party info"
THIRD_PARTY_LEVEL = logging.INFO

if __name__ == "__main__":
    setup(name="myapp")
    # app logger at DEBUG
    logging.getLogger(NAME).log(LEVEL, MSG)
    # third-party at INFO
    logging.getLogger(THIRD_PARTY).log(THIRD_PARTY_LEVEL, THIRD_PARTY_MSG)
