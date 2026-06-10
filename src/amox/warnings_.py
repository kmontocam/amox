"""Warning categories."""


class AmoxWarning(UserWarning):
    """Base warning for the amox library."""


class AmoxConfigWarning(AmoxWarning):
    """
    Invalid configuration value.

    Emitted when an environment variable or function argument holds an
    unsupported value.
    """


class AmoxFormatWarning(AmoxWarning):
    """
    Conflicting formatting or setup options.

    Emitted when formatting options are passed to a logger that is already
    configured.
    """
