"""Clients that meet: one invites, its rival accepts, the time between measured."""

import asyncio
import dataclasses
import typing as t

from ingots.perf import CsvSeed, LoadClient, LoadGroup, PerfUnit
from ingots.puer import Slot

from tests.perf.fixtures import ScenariosProject


@dataclasses.dataclass
class Pair:
    inviter: str
    invitee: str
    rank: int
    is_ranked: bool


class Inviter(LoadClient["PerfProject", "DuelGroup"]):
    @t.override
    async def run(self) -> None:
        self.group.invitations += 1
        key = f"{self.group.seeded.inviter}-{self.group.invitations}"
        async with self.measure("invite"):
            await self.project.echo.echo(key)
        self.group.start("invited-to-accepted", key)
        await self.group.queue.put(key)
        await asyncio.sleep(0.001)


class Invitee(LoadClient["PerfProject", "DuelGroup"]):
    @t.override
    async def run(self) -> None:
        key = await self.group.queue.get()
        self.group.finish("invited-to-accepted", key)


class DuelGroup(LoadGroup[Pair]):
    clients = (Inviter, Invitee)

    @t.override
    async def asyncSetUp(self) -> None:
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.invitations = 0


class PairsSeed(CsvSeed[Pair]):
    @t.override
    async def _make(self, groups: int) -> list[Pair]:
        return [
            Pair(f"a{index}", f"b{index}", index, index % 2 == 0)
            for index in range(groups)
        ]


class DuelPerf(PerfUnit[Pair]):
    group = DuelGroup
    seed = Slot(PairsSeed)


class PerfProject(ScenariosProject):
    perf = Slot(DuelPerf)
