"""
The demo of ingots: an application of the defaults alone, its configs,
its domain, a component, and its commands on the command line.
"""

import asyncio
import logging
import typing as t

from ingots.defaults import Project
from ingots.puer import Component, Slot, Unit

from extensions.cli import DemoCliUnit
from extensions.settings import DemoSettingsUnit

logger = logging.getLogger(__name__)


class DemoClock(Component):
    """Tells the time every ``DEMO_TICK`` seconds while it runs."""

    project: "DemoProject"

    @t.override
    async def _configure(self) -> None:
        await super()._configure()
        self._task = asyncio.create_task(self._tick())

    @t.override
    async def _shut_down(self) -> None:
        self._task.cancel()
        await super()._shut_down()

    async def _tick(self) -> None:
        while True:
            logger.info("tick")
            await asyncio.sleep(self.project.settings.configs.DEMO_TICK)


class GreetingsUnit(Unit):
    """Greets: the domain of the demo."""

    project: "DemoProject"
    clock = Slot(DemoClock)

    def greet(self, name: str, tone: str) -> str:
        greeting = self.project.settings.configs.DEMO_GREETING
        return f"{greeting}, {name}{'.' if tone == 'formal' else '!'}"


class DemoProject(Project):
    env_configs_prefix = "DEMO"
    settings = Slot(DemoSettingsUnit)
    greetings = Slot(GreetingsUnit)
    cli = Slot(DemoCliUnit)
