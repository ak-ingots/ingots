"""
The load of a project: what is loaded and how, against a target already
up. A scenario is a module, ``scenarios/<name>.py`` of a stand, giving
``PerfProject``: the project of the client it loads with the unit ``perf``,
a :class:`PerfUnit`, its group of clients, its seed, its report. How a run
is carried out on a host, the roles brought up, the cores, the rounds, is
the runner's, outside: ``python -m ingots.perf <module> perf plan`` gives
it the configs, ``seed`` and ``point`` do the load.
"""

__all__ = (
    "AnalyzeCliArgs",
    "AnalyzeCommand",
    "Call",
    "Comparison",
    "CsvReport",
    "CsvSeed",
    "LoadCliArgs",
    "LoadClient",
    "LoadCommand",
    "LoadGroup",
    "MedianAnalysis",
    "PerfConfigs",
    "PerfUnit",
    "PlanCommand",
    "PointCliArgs",
    "PointCommand",
    "Recorder",
    "ReportRow",
    "Rounds",
    "ScenarioModuleError",
    "SeedCommand",
    "Series",
    "SmokeCommand",
    "SmokeFailedError",
    "find_configs_files",
    "get_stand",
    "iter_perf_configs",
    "load_scenario",
    "run_scenario",
)

import platform
import sys
import time
import typing as t
from pathlib import Path

from ingots.puer import Slot
from ingots.puer.cli import CliUnit

from .clients import Call, LoadClient, LoadGroup, Recorder
from .analyses import Comparison, MedianAnalysis, Rounds, Series
from .commands import (
    AnalyzeCliArgs,
    AnalyzeCommand,
    LoadCliArgs,
    LoadCommand,
    PlanCommand,
    PointCliArgs,
    PointCommand,
    SeedCommand,
    SmokeCommand,
)
from .configs import PerfConfigs, iter_perf_configs
from .errors import ScenarioModuleError, SmokeFailedError
from .loader import find_configs_files, get_stand, load_scenario, run_scenario
from .reports import CsvReport, ReportRow
from .seeds import CsvSeed

if t.TYPE_CHECKING:
    from collections.abc import Sequence

    from ingots.defaults import Project


class PerfUnit[RowType](CliUnit):
    """
    The unit ``perf`` of a scenario: its :attr:`group`, a
    :class:`LoadGroup` of ``RowType`` rows, what it seeds in the slot
    ``seed``, a :class:`CsvSeed` of the same rows, its report in the slot
    ``report``, its analysis in the slot ``analysis``; its commands
    ``seed``, ``point``, ``load``, ``smoke``, ``plan`` and ``analyze``. Its
    project's configs are :class:`PerfConfigs`.
    """

    cli_description = "The load of the scenario."
    project: "Project"
    group: type[LoadGroup[RowType]]
    seed: Slot[CsvSeed[RowType]] = Slot(CsvSeed)
    report = Slot(CsvReport)
    analysis = Slot(MedianAnalysis)
    cmd_seed = Slot(SeedCommand)
    cmd_point = Slot(PointCommand)
    cmd_load = Slot(LoadCommand)
    cmd_smoke = Slot(SmokeCommand)
    cmd_plan = Slot(PlanCommand)
    cmd_analyze = Slot(AnalyzeCommand)

    def __init__(self) -> None:
        super().__init__()
        if not isinstance(getattr(type(self), "group", None), type):
            raise TypeError(f"{type(self).__qualname__}: no group of clients")
        if not isinstance(self.project.settings.configs, PerfConfigs):
            raise TypeError(
                f"{type(self).__qualname__}: the configs of the project are "
                "no PerfConfigs"
            )

    def _get_configs(self) -> PerfConfigs:
        return t.cast(PerfConfigs, self.project.settings.configs)

    def _get_scenario(self) -> str:
        """The name of the scenario, that of its module."""
        module = sys.modules[type(self.project).__module__]
        return Path(t.cast(str, module.__file__)).stem

    def _get_run(self) -> str:
        """The run, ``PERF_RUN``, or one of now: ``<date>-<time>-<host>``."""
        run = self._get_configs().PERF_RUN
        if not run:
            run = f"{time.strftime('%Y%m%d-%H%M%S')}-{platform.node()}"
        return run

    def _get_report_path(self) -> Path:
        """The report of the run, its name with no suffix."""
        reports = get_stand(self.project) / self._get_configs().PERF_REPORTS
        return reports / self._get_scenario() / self._get_run()

    async def _create_group(
        self, index: int, rows: "Sequence[RowType]", recorder: Recorder
    ) -> list[LoadClient[t.Any, t.Any]]:
        """The clients of group ``index``, set up, its row ``index`` in turn."""
        row = rows[index % len(rows)] if rows else t.cast(RowType, None)
        group = self.group(row, recorder)
        await group.asyncSetUp()
        clients: list[LoadClient[t.Any, t.Any]] = [
            cls(self.project, group) for cls in group.clients
        ]
        for client in clients:
            await client.asyncSetUp()
        return clients
