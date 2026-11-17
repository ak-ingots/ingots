"""
A project of scenarios, run by ``testing run`` in the tests of the command:
out of the discovery of the suite, ``runs/`` being no package.
"""

import typing as t

from ingots.defaults.settings import SettingsUnit
from ingots.defaults.settings.configs import Configs, IntConfig, StrConfig
from ingots.puer import Slot
from ingots.testing import TestingProject

# what the scenarios saw, read by the tests of the command
SEEN: list[dict[str, t.Any]] = []


class PlayConfigs(Configs):
    PLAY_HOST = StrConfig("localhost")
    PLAY_PORT = IntConfig(50051)
    PLAY_NAME = StrConfig("default")


class PlaySettingsUnit(SettingsUnit):
    configs = Slot(PlayConfigs)


class PlayProject(TestingProject):
    env_configs_prefix = "PLAY"
    settings = Slot(PlaySettingsUnit)
