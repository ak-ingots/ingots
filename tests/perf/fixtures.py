"""
The project of the scenarios of the tests: a client of no server, its calls
a turn of the event loop; ``stand/`` its stand, its modules loaded by path.
"""

import asyncio
import pathlib

from ingots.defaults import Project
from ingots.defaults.settings import SettingsUnit
from ingots.defaults.settings.configs import IntConfig
from ingots.puer import Entity, Slot
from ingots.perf import PerfConfigs

STAND = pathlib.Path(__file__).parent / "stand"


class EchoClient(Entity):
    """The client of the scenarios: an echo of no server."""

    async def echo(self, text: str) -> str:
        await asyncio.sleep(0)
        return text


class ScenariosConfigs(PerfConfigs):
    ECHO_PAUSE_MS = IntConfig(0)


class ScenariosSettingsUnit(SettingsUnit):
    configs = Slot(ScenariosConfigs)


class ScenariosProject(Project):
    env_configs_prefix = "PERF_TEST"
    settings = Slot(ScenariosSettingsUnit)
    echo = Slot(EchoClient)
