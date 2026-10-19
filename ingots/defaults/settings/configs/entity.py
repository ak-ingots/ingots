"""The configs: the flat namespace of the configs of a project."""

__all__ = ("Configs", "get_config", "iter_configs")

import inspect
import types
import typing as t

from ingots.puer.entity import Entity

from .base import BaseConfig
from .standard import BoolConfig

if t.TYPE_CHECKING:
    from collections.abc import Iterator, Mapping


class Configs(Entity):
    """
    The configs of a project, one namespace for all: an addon adds its own in
    a subclass, prefixed with its name (``HTTP_PORT``), and narrows the slot
    of the settings to it. A config reads its default until the settings
    apply the values, once, while the project is configured; from then on
    the configs are frozen.
    """

    IS_PRINT_CONFIGS = BoolConfig(True)

    # replaced, never changed: the instance gets its own when applied
    _configs_values: "Mapping[str, object]" = types.MappingProxyType({})
    _configs_applied = False

    def apply(self, values: "Mapping[str, object]") -> None:
        """
        Sets configs to ``values`` by name, the others keep their defaults,
        and freezes them all.

        :raises RuntimeError: the values are applied already.
        :raises KeyError: a name is not a config.
        :raises TypeError: a value does not fit its config.
        """
        if self._configs_applied:
            raise RuntimeError(f"{type(self).__qualname__}: the values are applied")
        cls = type(self)
        for name, value in values.items():
            get_config(cls, name).validate(value)
        self._configs_values = types.MappingProxyType(dict(values))
        self._configs_applied = True


def get_config(cls: type[Configs], name: str) -> BaseConfig[t.Any]:
    """
    The config of a configs class by name.

    :raises KeyError: the name is not a config.
    """
    config = inspect.getattr_static(cls, name, None)
    if not isinstance(config, BaseConfig):
        raise KeyError(f"{cls.__qualname__}: no config {name!r}")
    return config


def iter_configs(cls: type[Configs]) -> "Iterator[BaseConfig[t.Any]]":
    """The configs of a configs class, own and inherited, sorted by name."""
    for name in dir(cls):  # sorted, inherited names included
        config = inspect.getattr_static(cls, name)
        if isinstance(config, BaseConfig):
            yield config
