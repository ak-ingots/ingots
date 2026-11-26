"""The configs of the demo, ``DEMO_*``, mixed into those of the defaults."""

from ingots.defaults.settings import SettingsUnit
from ingots.defaults.settings.configs import Configs, FloatConfig, StrConfig
from ingots.puer import Slot


class DemoConfigs(Configs):
    DEMO_GREETING = StrConfig("Hello")
    DEMO_TICK = FloatConfig(1.0)


class DemoSettingsUnit(SettingsUnit):
    configs = Slot(DemoConfigs)
