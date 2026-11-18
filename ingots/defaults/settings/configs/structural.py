"""Configs of several values."""

__all__ = ("ListConfig", "TupleConfig")

import json
import typing as t

from .base import BaseConfig


class TupleConfig[TupleType: tuple[t.Any, ...]](BaseConfig[TupleType]):
    """
    A tuple shaped as its default: the same length, an item of the same
    type at each index. Converts a list and a string with a JSON array:
    ``["localhost", 8080]``.
    """

    @t.override
    def validate(self, value: object) -> None:
        if not isinstance(value, tuple):
            raise TypeError(f"{self.name}: {self._show(value)} is not a tuple")
        if len(value) != len(self.default):
            raise TypeError(
                f"{self.name}: {self._show(value)} has {len(value)} items, "
                f"not {len(self.default)}"
            )
        for index, (item, default) in enumerate(zip(value, self.default)):
            if not isinstance(item, type(default)):
                raise TypeError(
                    f"{self.name}: item {index} of {self._show(value)} is not "
                    f"a {type(default).__qualname__}"
                )

    @t.override
    def _parse(self, data: object) -> TupleType:
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                raise ValueError(
                    f"{self.name}: {self._show(data)} is not JSON"
                ) from None
        if isinstance(data, (tuple, list)):
            return t.cast(TupleType, tuple(data))
        self._reject(data)


class ListConfig[ItemType](BaseConfig[tuple[ItemType, ...]]):
    """
    Items of one type, as many as given: ``ListConfig(int, (1, 2, 4))``
    takes ``[1, 256]`` too. The value is a tuple, read-only as every config.
    Converts a list and a string with a JSON array: ``[1, 2, 4]``. A bool is
    not an item of an int, as :class:`IntConfig` takes none.
    """

    def __init__(self, item_type: type[ItemType], default: tuple[ItemType, ...] = ()):
        self._item_type = item_type
        super().__init__(default)

    @property
    def item_type(self) -> type[ItemType]:
        """The type of every item."""
        return self._item_type

    @t.override
    def __repr__(self) -> str:
        item_type = self._item_type.__qualname__
        return f"{type(self).__qualname__}({item_type}, {self.default!r})"

    @t.override
    def validate(self, value: object) -> None:
        if not isinstance(value, tuple):
            raise TypeError(f"{self.name}: {self._show(value)} is not a tuple")
        for index, item in enumerate(value):
            is_bool = isinstance(item, bool) and self._item_type is not bool
            if is_bool or not isinstance(item, self._item_type):
                raise TypeError(
                    f"{self.name}: item {index} of {self._show(value)} is not "
                    f"a {self._item_type.__qualname__}"
                )

    @t.override
    def _parse(self, data: object) -> tuple[ItemType, ...]:
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                raise ValueError(
                    f"{self.name}: {self._show(data)} is not JSON"
                ) from None
        if isinstance(data, (tuple, list)):
            return tuple(data)
        self._reject(data)
