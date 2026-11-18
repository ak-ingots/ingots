"""An echo: a client alone, nothing seeded."""

import asyncio
import typing as t

from ingots.perf import LoadClient, LoadGroup, PerfUnit
from ingots.puer import Slot

from tests.perf.fixtures import ScenariosProject


class Echo(LoadClient["PerfProject", "EchoGroup"]):
    @t.override
    async def run(self) -> None:
        async with self.measure("echo"):
            await self.project.echo.echo("hello")
        pause = self.project.settings.configs.ECHO_PAUSE_MS
        await asyncio.sleep(pause / 1000)


class EchoGroup(LoadGroup[None]):
    clients = (Echo,)


class EchoPerf(PerfUnit[None]):
    group = EchoGroup


class PerfProject(ScenariosProject):
    perf = Slot(EchoPerf)
