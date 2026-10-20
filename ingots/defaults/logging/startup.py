"""The startup logging: what is logged before the settings are configured."""

__all__ = (
    "INGOTS_LOGGING_MARKER",
    "STARTUP_LOGGING_FORMAT",
    "configure_startup_logging",
)

import logging

STARTUP_LOGGING_FORMAT = "%(levelname)s ▶ %(message)s ▶ %(name)s:%(lineno)s"
INGOTS_LOGGING_MARKER = "◈◈◈"


def configure_startup_logging(level: int | str = logging.WARNING) -> None:
    """
    Logs to the standard error until the logging unit is configured: called
    in the entry point, before the runner. A lower level, ``logging.DEBUG``
    for example, shows what happens at the very start of the process.
    """
    logging.basicConfig(level=level, format=STARTUP_LOGGING_FORMAT, force=True)
