"""The settings: the unit of the configs and what serves them."""

__all__ = ("ConfigsError", "Settings")

import inspect
import logging
import typing as t

from ingots.puer import Slot
from ingots.puer.cli import CliUnit

from .commands import ListConfigsCommand
from .configs import Configs, get_config, iter_configs
from .loaders import BaseLoader, CliLoader, EnvLoader, FileLoader

if t.TYPE_CHECKING:
    from collections.abc import Sequence

    from .loaders import Overrides

logger = logging.getLogger(__name__)


class Settings(CliUnit):
    """
    Holds the configs of the project and everything serving them; on the
    command line, the ``settings`` commands.

    Configuring the settings runs in two phases. The loaders of
    :attr:`LOADERS` collect the overrides of their sources, the later
    winning: the files, the environment, the command line. Then the settings
    convert them and apply them to the configs, which freezes them, and
    print the configs when ``IS_PRINT_CONFIGS`` is on. A wrong override (an
    unknown name, data that does not convert, a source that cannot be read)
    fails the configuration when ``IS_STRICT_CONFIGS`` is on, read from the
    overrides too, and is logged and ignored otherwise.

    An addon with configs of its own narrows :attr:`configs` in a subclass:
    ``configs = Slot(HttpConfigs)``; one with another source adds a loader
    slot and its name to :attr:`LOADERS`.
    """

    LOADERS: t.ClassVar[tuple[str, ...]] = ("file_loader", "env_loader", "cli_loader")

    cli_description = "The settings of the project."
    configs = Slot(Configs)
    file_loader = Slot(FileLoader)
    env_loader = Slot(EnvLoader)
    cli_loader = Slot(CliLoader)
    list = Slot(ListConfigsCommand)

    @t.override
    @classmethod
    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        for name in cls.LOADERS:
            slot = inspect.getattr_static(cls, name, None)
            if not (isinstance(slot, Slot) and issubclass(slot.cls, BaseLoader)):
                raise TypeError(
                    f"{cls.__qualname__}.LOADERS: {name!r} is not a slot of a loader"
                )

    async def configure(self) -> None:
        """Loads and applies the overrides, then prints the configs if asked."""
        self.configs.apply(self.convert_overrides(await self.load_overrides()))
        if self.configs.IS_PRINT_CONFIGS:
            self.print_configs()

    async def load_overrides(self) -> tuple["Overrides", ...]:
        """The overrides of every loader of :attr:`LOADERS`, in its order."""
        overrides: tuple["Overrides", ...] = ()
        for name in self.LOADERS:
            loader: BaseLoader = getattr(self, name)
            overrides += tuple(await loader.load())
        return overrides

    def convert_overrides(self, overrides: "Sequence[Overrides]") -> dict[str, object]:
        """
        The values of the configs for the overrides, the later winning.

        :raises ConfigsError: an override is wrong and ``IS_STRICT_CONFIGS``
            is on.
        """
        problems = [problem for item in overrides for problem in item.problems]
        sources = {
            name: (data, item.source)
            for item in overrides
            for name, data in item.data.items()
        }
        cls, values = type(self.configs), {}
        for name, (data, source) in sources.items():
            try:
                values[name] = get_config(cls, name).deserialize(data)
            except KeyError:
                problems.append(f"{source}: no config {name}")
            except (TypeError, ValueError) as error:
                problems.append(f"{source}: {error}")

        if not problems:
            return values

        if self._is_strict(values, sources):
            for problem in problems:
                logger.error("%s", problem)
            raise ConfigsError.from_problems(problems)
        for problem in problems:
            logger.warning("%s; ignored", problem)
        return values

    def print_configs(self) -> None:
        """Prints every config with its value, sorted by name; secrets masked."""
        configs = self.configs
        print("Configs:")
        for config in iter_configs(type(configs)):
            print(f"{config.name} = {config.format_value(config.get_value(configs))}")
        print("-" * 12)

    def _is_strict(self, values: dict[str, object], sources: dict[str, t.Any]) -> bool:
        name = Configs.IS_STRICT_CONFIGS.name
        if name in values:
            return bool(values[name])
        # an override that does not convert cannot loosen the mode
        return name in sources or self.configs.IS_STRICT_CONFIGS


class ConfigsError(Exception):
    """
    The overrides of the configs are wrong. ``args`` are the message and
    the problems, so the error survives pickling; create it with
    :meth:`from_problems`.
    """

    @classmethod
    def from_problems(cls, problems: "Sequence[str]") -> t.Self:
        """The error of the problems, one line each, logged already."""
        count = len(problems)
        return cls(
            f"{count} wrong override{'s' if count > 1 else ''} of the configs",
            tuple(problems),
        )

    @property
    def problems(self) -> tuple[str, ...]:
        """The problems, one line each."""
        return t.cast(tuple[str, ...], self.args[1])

    @t.override
    def __str__(self) -> str:
        return t.cast(str, self.args[0])
