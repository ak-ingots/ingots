"""The commands of the logging."""

__all__ = ("LoggingInfoCommand",)

import typing as t

from ingots.puer.cli import BaseCommand

if t.TYPE_CHECKING:
    from ingots.defaults.project import Project


class LoggingInfoCommand(BaseCommand):
    """Prints the logging configuration the project runs with."""

    cli_description = "Prints the logging configuration of the project."
    project: "Project"

    @t.override
    async def _run(self) -> None:
        self.project.logging.print_config()
