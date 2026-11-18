"""The seed of a scenario: what it needs ahead, in ``seed.csv``."""

__all__ = ("CsvSeed",)

import csv
import dataclasses
import types
import typing as t
from pathlib import Path

from ingots.puer import Entity

from .configs import PerfConfigs

if t.TYPE_CHECKING:
    from collections.abc import Sequence

    from ingots.defaults import Project


class CsvSeed[RowType](Entity):
    """
    What a scenario needs ahead, the players of a game, rows of a dataclass
    of ``RowType`` made by :meth:`_make` through the API of the application,
    by its client, none by default; kept in ``seed.csv`` of ``PERF_WORK``,
    or the file of ``PERF_SEED_FILE``, their fields its header, read back by
    their annotations. A scenario seeding gives its own in the slot ``seed``
    of its unit: ``seed = Slot(PlayersSeed)``, ``PlayersSeed(CsvSeed[Player])``.
    """

    project: "Project"

    @property
    def path(self) -> Path:
        """The file of the rows."""
        configs = t.cast(PerfConfigs, self.project.settings.configs)
        return Path(configs.PERF_SEED_FILE or Path(configs.PERF_WORK, "seed.csv"))

    async def write(self, groups: int) -> int:
        """
        Makes the rows of ``groups`` groups into the file, none removing it,
        so that no point reads the rows of another run; the rows made.
        """
        rows = await self._make(groups)
        path = self.path
        if not rows:
            path.unlink(missing_ok=True)
            return 0
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = [field.name for field in dataclasses.fields(t.cast(t.Any, rows[0]))]
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fields)
            writer.writeheader()
            writer.writerows(dataclasses.asdict(t.cast(t.Any, row)) for row in rows)
        return len(rows)

    def read(self) -> "Sequence[RowType]":
        """The rows of the file, none without it."""
        path = self.path
        if not path.exists():
            return []
        cls = self._get_row_type()
        hints = t.get_type_hints(cls)
        with path.open(newline="", encoding="utf-8") as file:
            return [
                cls(**{name: convert(hints[name], data) for name, data in row.items()})
                for row in csv.DictReader(file)
            ]

    async def _make(self, groups: int) -> "Sequence[RowType]":
        """
        The rows the scenario needs ahead for ``groups`` groups, made through
        the API of the application by its client; none by default. Group
        ``i`` of a point takes row ``i`` in turn.
        """
        return ()

    def _get_row_type(self) -> type[RowType]:
        """The dataclass of the rows, that of the class: ``CsvSeed[Player]``."""
        for cls in type(self).__mro__:
            for base in types.get_original_bases(cls):
                if t.get_origin(base) is CsvSeed:
                    return t.cast(type[RowType], t.get_args(base)[0])
        raise TypeError(f"{type(self).__qualname__}: no type of the rows")


def convert(kind: object, data: str) -> object:
    """A field of a row from its text, by its annotation."""
    if kind is bool:
        return data == "True"
    return t.cast(t.Callable[[str], object], kind)(data)
