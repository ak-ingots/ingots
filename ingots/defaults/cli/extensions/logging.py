"""The commands of the logging."""

__all__ = (
    "LoggingCommandsUnit",
    "LoggingInfoCommand",
)

import typing as t

from ingots.puer import Slot

from ..command import BaseCommand
from ..unit import CommandsUnit

if t.TYPE_CHECKING:
    from ingots.defaults.project import Project


class LoggingInfoCommand(BaseCommand):
    """Prints the logging configuration the project runs with."""

    cli_is_quiet = True
    cli_description = "Prints the logging configuration of the project."
    project: "Project"

    @t.override
    async def _run(self) -> None:
        self.project.logging.print_config()


class LoggingCommandsUnit(CommandsUnit):
    """``logging``: ``info``."""

    cli_description = "The logging of the project."
    info = Slot(LoggingInfoCommand)
