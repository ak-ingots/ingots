"""An addon with configs of its own, and an application joining two addons."""

import enum

from ingots.defaults import Project
from ingots.defaults.settings import Settings
from ingots.defaults.settings.configs import (
    BoolConfig,
    Configs,
    EnumConfig,
    IntConfig,
    SecureStrConfig,
    StrConfig,
    TupleConfig,
)
from ingots.puer import Slot


class Mode(enum.Enum):
    FAST = "fast"
    SAFE = "safe"


class HttpConfigs(Configs):
    IS_PRINT_CONFIGS = BoolConfig(False)
    HTTP_PORT = IntConfig(8080)
    HTTP_BIND = TupleConfig(("localhost", 8080))
    HTTP_TOKEN = SecureStrConfig("secret")


class HttpSettings(Settings):
    configs = Slot(HttpConfigs)


class HttpProject(Project):
    settings = Slot(HttpSettings)


class DbConfigs(Configs):
    DB_NAME = StrConfig("app")
    DB_MODE = EnumConfig(Mode.SAFE)


class DbSettings(Settings):
    configs = Slot(DbConfigs)


class DbProject(Project):
    settings = Slot(DbSettings)


class AppConfigs(HttpConfigs, DbConfigs):
    pass


class AppSettings(HttpSettings, DbSettings):
    configs = Slot(AppConfigs)


class AppProject(HttpProject, DbProject):
    settings = Slot(AppSettings)


class LoadedSettings(AppSettings):
    """Loads values other than the defaults, as a source would."""

    async def load_values(self) -> dict[str, object]:
        return {"IS_PRINT_CONFIGS": True, "HTTP_PORT": 9090, "DB_MODE": Mode.FAST}


class LoadedProject(AppProject):
    settings = Slot(LoadedSettings)
