"""The report of a run: its data in a CSV, the run in an INI."""

__all__ = ("CsvReport", "ReportRow")

import configparser
import csv
import dataclasses
import os
import platform
import typing as t

from ingots.puer import Entity

from .configs import PerfConfigs, iter_perf_configs

if t.TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path

    from ingots.defaults import Project


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ReportRow:
    """A row of the CSV of a report: a metric of an action at a point of a round."""

    role: str
    round: int
    action: str
    groups: int
    metric: str
    value: str


FIELDS = tuple(field.name for field in dataclasses.fields(ReportRow))

# the configs a point tells of its role, apart from those of the run
ROLE_CONFIGS = frozenset(
    {"PERF_ROLE", "PERF_ROUND", "PERF_REF", "PERF_COMMIT", "PERF_SERVERS"}
)


class CsvReport(Entity):
    """
    The report of a run, two files of one name: the CSV, the data alone,
    what changes from a row to the next, a metric a row, appended point by
    point; the INI, the run, a section a part of it, its options merged
    point by point. A scenario shapes its own by a subclass in the slot
    ``report`` of its unit.
    """

    project: "Project"

    def append_point(self, path: "Path", rows: "Iterable[ReportRow]") -> None:
        """
        The rows of a point into the report of its run, ``path`` its name
        with no suffix: the CSV appended, the INI told of the run, the host
        and the role of the point.
        """
        configs = t.cast(PerfConfigs, self.project.settings.configs)
        self.append(path.with_suffix(".csv"), rows)
        shown = {
            config.name: show_config(getattr(configs, config.name))
            for config in iter_perf_configs()
        }
        run = {name: value for name, value in shown.items() if name not in ROLE_CONFIGS}
        role = {name: value for name, value in shown.items() if name in ROLE_CONFIGS}
        host = describe_host() | {"state": configs.PERF_HOST_STATE}
        self.write_run(
            path.with_suffix(".ini"),
            {"run": run, "host": host, f"role {configs.PERF_ROLE}": role},
        )

    def append(self, path: "Path", rows: "Iterable[ReportRow]") -> None:
        """Appends the rows to the CSV, its header first when it is new."""
        path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, FIELDS)
            if is_new:
                writer.writeheader()
            writer.writerows(dataclasses.asdict(row) for row in rows)

    def read(self, path: "Path") -> "Sequence[ReportRow]":
        """The rows of the CSV."""
        with path.open(newline="", encoding="utf-8") as file:
            return [
                ReportRow(
                    role=row["role"],
                    round=int(row["round"]),
                    action=row["action"],
                    groups=int(row["groups"]),
                    metric=row["metric"],
                    value=row["value"],
                )
                for row in csv.DictReader(file)
            ]

    def write_run(
        self, path: "Path", sections: "Mapping[str, Mapping[str, str]]"
    ) -> None:
        """Merges the sections into the INI of the run, an option replacing its own."""
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str  # type: ignore[assignment,method-assign]
        parser.read(path, encoding="utf-8")
        for name, options in sections.items():
            if not parser.has_section(name):
                parser.add_section(name)
            for option, value in options.items():
                parser.set(name, option, value)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            parser.write(file)


def show_config(value: object) -> str:
    """A config as the shell and the INI take it: a list its items apart by spaces."""
    return " ".join(map(str, value)) if isinstance(value, tuple) else str(value)


def describe_host() -> dict[str, str]:
    """The host of a run as its INI keeps it."""
    return {
        "name": platform.node(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "kernel": platform.release(),
        "python": platform.python_version(),
        "cpus": str(os.cpu_count()),
    }
