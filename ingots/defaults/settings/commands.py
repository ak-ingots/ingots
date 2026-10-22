"""The commands of the settings."""

__all__ = ("ListConfigsCommand",)

import typing as t

from ingots.puer.cli import BaseCommand

if t.TYPE_CHECKING:
    from ingots.defaults.project import Project


class ListConfigsCommand(BaseCommand):
    """Prints the configs the project runs with."""

    cli_description = "Prints the configs of the project."
    project: "Project"

    @t.override
    async def _run(self) -> None:
        self.project.settings.print_configs()
