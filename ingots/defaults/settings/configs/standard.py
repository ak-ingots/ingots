"""Configs of the built-in scalar types."""

__all__ = (
    "BoolConfig",
    "DecimalConfig",
    "FloatConfig",
    "IntConfig",
    "SecureStrConfig",
    "StrConfig",
)

import decimal
import typing as t

from .base import BaseConfig


class BoolConfig(BaseConfig[bool]):
    """
    A flag. Converts ``1``/``0``, ``true``/``false``, ``yes``/``no`` and
    ``on``/``off`` in any case; anything else is an error, not a false.
    """

    TRUE_STRINGS: t.ClassVar[frozenset[str]] = frozenset({"1", "true", "yes", "on"})
    FALSE_STRINGS: t.ClassVar[frozenset[str]] = frozenset({"0", "false", "no", "off"})

    def validate(self, value: object) -> None:
        if not isinstance(value, bool):
            raise TypeError(f"{self.name}: {self._show(value)} is not a bool")

    def _parse(self, data: object) -> bool:
        match data:
            case bool():
                return data
            case int() if data in (0, 1):
                return bool(data)
            case str() if data.lower() in self.TRUE_STRINGS:
                return True
            case str() if data.lower() in self.FALSE_STRINGS:
                return False
            case str():
                raise ValueError(f"{self.name}: {self._show(data)} is not a bool")
        self._reject(data)


class IntConfig(BaseConfig[int]):
    """An integer. Converts a string and a float without a fraction."""

    def validate(self, value: object) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{self.name}: {self._show(value)} is not an int")

    def _parse(self, data: object) -> int:
        match data:
            case bool():
                pass
            case int():
                return data
            case float() if data.is_integer():
                return int(data)
            case float():
                raise ValueError(f"{self.name}: {self._show(data)} has a fraction")
            case str():
                try:
                    return int(data)
                except ValueError:
                    raise ValueError(
                        f"{self.name}: {self._show(data)} is not an int"
                    ) from None
        self._reject(data)


class FloatConfig(BaseConfig[float]):
    """A float; an int is a float too. Converts a string."""

    def validate(self, value: object) -> None:
        if not isinstance(value, (float, int)) or isinstance(value, bool):
            raise TypeError(f"{self.name}: {self._show(value)} is not a float")

    def _parse(self, data: object) -> float:
        match data:
            case bool():
                pass
            case float() | int():
                return float(data)
            case str():
                try:
                    return float(data)
                except ValueError:
                    raise ValueError(
                        f"{self.name}: {self._show(data)} is not a float"
                    ) from None
        self._reject(data)


class DecimalConfig(BaseConfig[decimal.Decimal]):
    """
    A decimal. Converts a string, an int and a float, the float as it is
    written (``0.1``, not its binary approximation).
    """

    def validate(self, value: object) -> None:
        if not isinstance(value, decimal.Decimal):
            raise TypeError(f"{self.name}: {self._show(value)} is not a Decimal")

    def _parse(self, data: object) -> decimal.Decimal:
        match data:
            case bool():
                pass
            case decimal.Decimal():
                return data
            case int() | float():
                return decimal.Decimal(str(data))
            case str():
                try:
                    return decimal.Decimal(data)
                except decimal.InvalidOperation:
                    raise ValueError(
                        f"{self.name}: {self._show(data)} is not a decimal"
                    ) from None
        self._reject(data)


class StrConfig(BaseConfig[str]):
    """A string."""

    def validate(self, value: object) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{self.name}: {self._show(value)} is not a str")

    def _parse(self, data: object) -> str:
        if isinstance(data, str):
            return data
        self._reject(data)


class SecureStrConfig(StrConfig):
    """A secret string: printed as ``***``."""

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}('***')"

    def format_value(self, value: str) -> str:
        return "***"

    def _show(self, data: object) -> str:
        return "'***'"
