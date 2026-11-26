"""The project of the defaults."""

__all__ = ("Project",)

import typing as t

from ingots.puer import Project as BaseProject
from ingots.puer import Slot

from .cli import CliUnit
from .components import ComponentsUnit
from .events import EventsUnit
from .logging import LoggingUnit
from .operations import OperationsUnit
from .settings import SettingsUnit


class Project(BaseProject):
    """
    The project an application starts from: the standard units, the command
    line one of them, ``cli``. Configuring it configures the units in their
    order: the settings, then the logging from the configs unless
    ``IS_CONFIGURE_LOGGING`` is off; shutting it down waits for the
    subscribers of the events running, then shuts down the components it
    configured.

    The environment variables of the configs take :attr:`env_configs_prefix`:
    ``"INGOT"`` here, which an addon run on its own keeps, so ``INGOT_HTTP_PORT``
    sets the config ``HTTP_PORT``. An application sets its own: ``"APP"``
    reads ``APP_HTTP_PORT``.
    """

    env_configs_prefix: t.ClassVar[str] = "INGOT"

    settings = Slot(SettingsUnit)
    logging = Slot(LoggingUnit)
    components = Slot(ComponentsUnit)
    operations = Slot(OperationsUnit)
    events = Slot(EventsUnit)
    cli = Slot(CliUnit)

    @t.override
    async def _configure(self) -> None:
        await super()._configure()
        await self.settings.configure()
        if self.settings.configs.IS_CONFIGURE_LOGGING:
            await self.logging.configure()

    @t.override
    async def _shut_down(self) -> None:
        await super()._shut_down()
        await self.events.join()
