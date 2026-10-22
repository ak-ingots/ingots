"""Configs choosing one of a set."""

__all__ = ("EnumConfig", "LogLevelConfig")

import enum
import logging
import typing as t

from .base import BaseConfig
from .standard import IntConfig


class EnumConfig[EnumType: enum.Enum](BaseConfig[EnumType]):
    """A member of the enum of its default. Converts a member name."""

    @t.override
    def validate(self, value: object) -> None:
        if not isinstance(value, type(self.default)):
            raise TypeError(
                f"{self.name}: {self._show(value)} is not "
                f"a {type(self.default).__qualname__}"
            )

    @t.override
    def _parse(self, data: object) -> EnumType:
        enum_cls = type(self.default)
        if isinstance(data, enum_cls):
            return data
        if isinstance(data, str):
            try:
                return enum_cls[data]
            except KeyError:
                raise ValueError(
                    f"{self.name}: {self._show(data)} is not "
                    f"a member of {enum_cls.__qualname__}"
                ) from None
        self._reject(data)


class LogLevelConfig(IntConfig):
    """
    A logging level. Converts a level name in any case: ``info``; prints the
    name of a standard level.
    """

    @t.override
    def format_value(self, value: int) -> str:
        return logging.getLevelName(value)

    @t.override
    def _parse(self, data: object) -> int:
        if isinstance(data, str) and not data.lstrip("-").isdigit():
            try:
                return logging.getLevelNamesMapping()[data.upper()]
            except KeyError:
                raise ValueError(
                    f"{self.name}: {self._show(data)} is not a logging level"
                ) from None
        return super()._parse(data)
