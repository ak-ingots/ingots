"""A scenario of mistakes: an action that errs, a client that measures nothing."""

import typing as t
from ingots.defaults.settings.configs import BoolConfig
from ingots.perf import LoadClient, LoadGroup, PerfUnit
from ingots.puer import Slot

from tests.perf.fixtures import ScenariosConfigs, ScenariosProject
from tests.perf.fixtures import ScenariosSettingsUnit


class FailingConfigs(ScenariosConfigs):
    FAILING_IS_SILENT = BoolConfig(False)
    FAILING_IS_BROKEN = BoolConfig(False)


class FailingSettings(ScenariosSettingsUnit):
    configs = Slot(FailingConfigs)


class Failing(LoadClient["PerfProject", "FailingGroup"]):
    @t.override
    async def run(self) -> None:
        configs = self.project.settings.configs
        if configs.FAILING_IS_BROKEN:
            raise RuntimeError("a mistake of the scenario")
        if not configs.FAILING_IS_SILENT:
            async with self.measure("fail"):
                raise LookupError("no such player")


class FailingGroup(LoadGroup[None]):
    clients = (Failing,)


class FailingPerf(PerfUnit[None]):
    group = FailingGroup


class PerfProject(ScenariosProject):
    settings = Slot(FailingSettings)
    perf = Slot(FailingPerf)
