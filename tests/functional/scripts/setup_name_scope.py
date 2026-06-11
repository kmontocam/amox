"""Providing a name enables client visibility."""

import logging

from amox import setup

ROOT_NAME = "src"
MSG = "visible"
NAME = f"{ROOT_NAME}.service"
LEVEL = logging.DEBUG


if __name__ == "__main__":
    setup(name=ROOT_NAME)
    # logger at DEBUG, inside of tree
    logging.getLogger(NAME).log(LEVEL, MSG)
