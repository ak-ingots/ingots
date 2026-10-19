"""The project of the defaults."""

__all__ = ("Project",)

from ingots.puer import Slot
from ingots.puer.cli import CliProject

from .settings import Settings


class Project(CliProject):
    """
    The project an application starts from: a command-line project with the
    standard units. Configuring it configures the units in their order.
    """

    settings = Slot(Settings)

    async def configure(self) -> None:
        await super().configure()
        await self.settings.configure()
