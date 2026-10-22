"""Configs of dates and times, in the ISO 8601 format."""

__all__ = ("DateConfig", "DateTimeConfig", "TimeConfig")

import datetime
import typing as t

from .base import BaseConfig


class DateConfig(BaseConfig[datetime.date]):
    """A date, not a datetime. Converts an ISO 8601 string: ``2026-10-19``."""

    @t.override
    def validate(self, value: object) -> None:
        if not isinstance(value, datetime.date) or isinstance(value, datetime.datetime):
            raise TypeError(f"{self.name}: {self._show(value)} is not a date")

    @t.override
    def _parse(self, data: object) -> datetime.date:
        if isinstance(data, datetime.date):
            return data
        if isinstance(data, str):
            try:
                return datetime.date.fromisoformat(data)
            except ValueError:
                raise ValueError(
                    f"{self.name}: {self._show(data)} is not an ISO 8601 date"
                ) from None
        self._reject(data)


class TimeConfig(BaseConfig[datetime.time]):
    """A time of day. Converts an ISO 8601 string: ``12:30:00``."""

    @t.override
    def validate(self, value: object) -> None:
        if not isinstance(value, datetime.time):
            raise TypeError(f"{self.name}: {self._show(value)} is not a time")

    @t.override
    def _parse(self, data: object) -> datetime.time:
        if isinstance(data, datetime.time):
            return data
        if isinstance(data, str):
            try:
                return datetime.time.fromisoformat(data)
            except ValueError:
                raise ValueError(
                    f"{self.name}: {self._show(data)} is not an ISO 8601 time"
                ) from None
        self._reject(data)


class DateTimeConfig(BaseConfig[datetime.datetime]):
    """A date and time. Converts an ISO 8601 string: ``2026-10-19T12:30:00``."""

    @t.override
    def validate(self, value: object) -> None:
        if not isinstance(value, datetime.datetime):
            raise TypeError(f"{self.name}: {self._show(value)} is not a datetime")

    @t.override
    def _parse(self, data: object) -> datetime.datetime:
        if isinstance(data, datetime.datetime):
            return data
        if isinstance(data, str):
            try:
                return datetime.datetime.fromisoformat(data)
            except ValueError:
                raise ValueError(
                    f"{self.name}: {self._show(data)} is not an ISO 8601 datetime"
                ) from None
        self._reject(data)
