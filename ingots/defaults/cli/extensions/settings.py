"""The commands of the settings."""

__all__ = (
    "SettingsCommandsUnit",
    "ListConfigsCommand",
)

import typing as t

from ingots.puer import Slot

from ..command import BaseCommand
from ..unit import CommandsUnit

if t.TYPE_CHECKING:
    from ingots.defaults.project import Project


class ListConfigsCommand(BaseCommand):
    """Prints the configs the project runs with."""

    cli_is_quiet = True
    cli_description = "Prints the configs of the project."
    project: "Project"

    @t.override
    async def _run(self) -> None:
        self.project.settings.print_configs()


class SettingsCommandsUnit(CommandsUnit):
    """``settings``: ``list``."""

    cli_description = "The settings of the project."
    list = Slot(ListConfigsCommand)
