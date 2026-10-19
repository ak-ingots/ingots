"""The loader: a source of overrides for the configs."""

__all__ = ("BaseLoader", "Overrides")

import abc
import typing as t
from dataclasses import dataclass

from ingots.puer.entity import Entity

if t.TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True, slots=True)
class Overrides:
    """
    What a source sets: config names to their data, as the source has it (a
    string, a JSON value), and what went wrong loading it.
    """

    source: str
    data: "Mapping[str, object]"
    problems: tuple[str, ...] = ()


class BaseLoader(Entity):
    """
    Loads overrides for the configs from one kind of source: files, the
    environment, the command line, a secrets store. A loader only collects
    the data; the settings convert and apply it. A source it cannot read is
    a problem of its overrides, not an exception: the settings decide whether
    to fail.
    """

    @abc.abstractmethod
    async def load(self) -> list[Overrides]:
        """The overrides of the sources, in the order they apply."""
        raise NotImplementedError(f"{type(self).__qualname__}.load")
