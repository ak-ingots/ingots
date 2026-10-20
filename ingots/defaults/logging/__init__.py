"""The logging: the unit configuring the logging of the process."""

__all__ = ("Logging", "configure_startup_logging")

import logging
import logging.config
import typing as t

from ingots.puer import Slot
from ingots.puer.cli import CliUnit

from .commands import LoggingInfoCommand
from .context import LogContextFilter
from .startup import configure_startup_logging

if t.TYPE_CHECKING:
    from collections.abc import Mapping

    from ingots.defaults.project import Project


logger = logging.getLogger(__name__)


class Logging(CliUnit):
    """
    Configures the logging from the ``LOGGING_*`` configs, once the settings
    are configured; on the command line, the ``logging`` commands.

    The configuration is a :func:`logging.config.dictConfig` dictionary, built
    by part: a subclass extends :meth:`build_formatters`,
    :meth:`build_filters`, :meth:`build_handlers` or :meth:`build_loggers`
    to add its own. The logging is global to the process: the last project
    configured wins.
    """

    cli_description = "The logging of the project."
    project: "Project"
    info = Slot(LoggingInfoCommand)

    async def configure(self) -> None:
        """Applies the configuration built from the configs."""
        config = self.build_config()
        logger.debug("the logging configuration: %s", config)
        logging.config.dictConfig(config)

    def build_config(self) -> dict[str, t.Any]:
        """The :func:`logging.config.dictConfig` dictionary."""
        configs = self.project.settings.configs
        config: dict[str, t.Any] = {
            "version": 1,
            "disable_existing_loggers": configs.LOGGING_DISABLE_EXISTING_LOGGERS,
            "formatters": self.build_formatters(),
            "filters": self.build_filters(),
            "handlers": self.build_handlers(),
            "loggers": self.build_loggers(),
        }
        if configs.LOGGING_ENABLE_ROOT_LOGGER:
            config["root"] = {
                "level": configs.LOGGING_ROOT_LOGGER_LEVEL,
                "handlers": ["default"],
            }
        return config

    def build_formatters(self) -> dict[str, dict[str, t.Any]]:
        """The formatters, by name."""
        configs = self.project.settings.configs
        return {
            "default": {"format": configs.LOGGING_DEFAULT_FORMAT},
            "ingots": {"format": configs.LOGGING_INGOTS_FORMAT},
        }

    def build_filters(self) -> dict[str, dict[str, t.Any]]:
        """The filters, by name; ``cvars`` adds the log context."""
        return {"cvars": {"()": LogContextFilter}}

    def build_handlers(self) -> dict[str, dict[str, t.Any]]:
        """The handlers, by name; both write to the standard error."""
        return {
            name: {
                "class": "logging.StreamHandler",
                "formatter": name,
                "filters": ["cvars"],
            }
            for name in ("default", "ingots")
        }

    def build_loggers(self) -> dict[str, dict[str, t.Any]]:
        """The loggers, by name."""
        configs = self.project.settings.configs
        return {
            "ingots": {
                "level": configs.LOGGING_INGOTS_LEVEL,
                "handlers": ["ingots"],
                "propagate": False,
            },
        }

    def print_config(self) -> None:
        """Prints the configuration, one key a line, nested by indent."""
        print("Logging:")
        _print_mapping(self.build_config(), "    ")
        print("-" * 12)


def _print_mapping(mapping: "Mapping[str, t.Any]", indent: str) -> None:
    for key, value in mapping.items():
        if isinstance(value, dict):
            print(f"{indent}{key}:")
            _print_mapping(value, indent + "    ")
        else:
            print(f"{indent}{key}: {value!r}")
