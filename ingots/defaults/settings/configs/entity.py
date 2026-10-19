"""The configs: the flat namespace of the configs of a project."""

__all__ = ("Configs", "check_configs", "get_config", "iter_configs")

import inspect
import itertools
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

    ``IS_PRINT_CONFIGS`` prints the configs once applied; ``IS_STRICT_CONFIGS``
    fails the configuration on a wrong override instead of ignoring it.

    Joining the configs of addons checks the names when the class is
    created: see :func:`check_configs`.
    """

    IS_PRINT_CONFIGS = BoolConfig(True)
    IS_STRICT_CONFIGS = BoolConfig(False)

    # replaced, never changed: the instance gets its own when applied
    _configs_values: "Mapping[str, object]" = types.MappingProxyType({})
    _configs_applied = False

    @classmethod
    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        check_configs(cls)

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


def check_configs(cls: type[Configs]) -> None:
    """
    A config name declared by two unrelated bases is a clash: two addons
    chose one name for different configs. An override is not: a base that
    redeclares a config of a common ancestor wins over it. The subclass
    resolves a clash by declaring the config itself.
    """
    owners: dict[str, dict[type, None]] = {}  # ordered sets

    for base in cls.__bases__:
        seen: set[str] = set()
        for klass in base.__mro__:  # the first owner of a name is the base's
            for name, value in vars(klass).items():
                if name in seen:
                    continue
                seen.add(name)
                if isinstance(value, BaseConfig) and name not in vars(cls):
                    owners.setdefault(name, {})[klass] = None

    for name, classes in owners.items():
        for first, second in itertools.combinations(classes, 2):
            if not (issubclass(first, second) or issubclass(second, first)):
                raise TypeError(
                    f"{cls.__qualname__}: {first.__qualname__}.{name} and "
                    f"{second.__qualname__}.{name} are different configs: "
                    f"rename one, or declare {cls.__qualname__}.{name}"
                )


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
