"""
setup_after_get_logger: calls get_logger then setup, triggering handler removal.

When `setup()` runs after `get_logger()`, it emits a logging warning for each named
logger that had an amox-managed handler.
"""

from amox import get_logger, setup

LOGGER = "app.before_setup"

if __name__ == "__main__":
    _ = get_logger(LOGGER)
    setup()
