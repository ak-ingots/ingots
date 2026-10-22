"""Configs of several values."""

__all__ = ("TupleConfig",)

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
