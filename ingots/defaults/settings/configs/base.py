"""The config: one typed value of the configs."""

__all__ = ("BaseConfig",)

import abc
import typing as t

if t.TYPE_CHECKING:
    from .entity import Configs


class BaseConfig[ValueType]:
    """
    One config of :class:`~ingots.defaults.settings.configs.entity.Configs`: its
    default and the rules for its values. The value lives in the configs
    instance, so every project has its own; on the class it is the config
    itself. A config is read-only: the settings apply the values once.

    A subclass checks the type of value in :meth:`validate` and converts
    the data of a source (a string, a JSON value) in :meth:`_parse`.
    """

    def __init__(self, default: ValueType) -> None:
        self._name = type(self).__qualname__  # the attribute name once set
        self._default = default
        self.validate(default)

    @property
    def name(self) -> str:
        """The name of the config: its attribute name."""
        return self._name

    @property
    def default(self) -> ValueType:
        """The value of the config until the settings apply another one."""
        return self._default

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...

    @t.overload
    def __get__(self, obj: "Configs", owner: type) -> ValueType: ...

    def __get__(self, obj: "Configs | None", owner: type) -> t.Self | ValueType:
        if obj is None:
            return self
        return self.get_value(obj)

    def __set__(self, obj: "Configs", value: t.Never) -> t.NoReturn:
        raise AttributeError(f"{self._name} is read-only: the settings apply configs")

    @t.override
    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self._default!r})"

    def get_value(self, configs: "Configs") -> ValueType:
        """The value of the config in ``configs``."""
        return t.cast(ValueType, configs._configs_values.get(self._name, self._default))

    @abc.abstractmethod
    def validate(self, value: object) -> None:
        """
        Checks that ``value`` fits the config.

        :raises TypeError: it does not.
        """
        raise NotImplementedError(f"{type(self).__qualname__}.validate")

    def deserialize(self, data: object) -> ValueType:
        """
        Converts the data of a source to a value of the config.

        :raises TypeError: the data is of a type the config does not convert.
        :raises ValueError: the data does not convert.
        """
        value = self._parse(data)
        self.validate(value)
        return value

    def format_value(self, value: ValueType) -> str:
        """The value as it is printed."""
        return str(value)

    @abc.abstractmethod
    def _parse(self, data: object) -> ValueType:
        raise NotImplementedError(f"{type(self).__qualname__}._parse")

    def _reject(self, data: object) -> t.NoReturn:
        raise TypeError(
            f"{self._name}: cannot convert {type(data).__qualname__} "
            f"{self._show(data)}"
        )

    def _show(self, data: object) -> str:
        """Data or a value in an error message."""
        return repr(data)
