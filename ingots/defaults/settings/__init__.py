"""The settings: the unit of the configs and what serves them."""

__all__ = ("Settings",)

from ingots.puer import Slot
from ingots.puer.cli import CliUnit

from .commands import ListConfigsCommand
from .configs import Configs, iter_configs


class Settings(CliUnit):
    """
    Holds the configs of the project and everything serving them; on the
    command line, the ``settings`` commands. Configuring the settings applies
    the values loaded for the configs and freezes them, then prints them when
    ``IS_PRINT_CONFIGS`` is on.

    An addon with configs of its own narrows :attr:`configs` in a subclass:
    ``configs = Slot(HttpConfigs)``.
    """

    cli_description = "The settings of the project."
    configs = Slot(Configs)
    list = Slot(ListConfigsCommand)

    async def configure(self) -> None:
        """Applies the loaded values to the configs and prints them if asked."""
        self.configs.apply(await self.load_values())
        if self.configs.IS_PRINT_CONFIGS:
            self.print_configs()

    async def load_values(self) -> dict[str, object]:
        """The values of the configs other than their defaults: none here."""
        return {}

    def print_configs(self) -> None:
        """Prints every config with its value, sorted by name; secrets masked."""
        configs = self.configs
        print("Configs:")
        for config in iter_configs(type(configs)):
            print(f"{config.name} = {config.format_value(config.get_value(configs))}")
        print("-" * 12)
