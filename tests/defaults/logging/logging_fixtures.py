"""A project that logs: quiet configs, a logger of its own, the log context."""

import typing as t

from ingots.defaults import Project
from ingots.defaults.logging import Logging
from ingots.defaults.logging.context import LogContextVar
from ingots.defaults.settings import Settings
from ingots.defaults.settings.configs import BoolConfig, Configs
from ingots.puer import Slot

REQUEST_ID = LogContextVar[str]("test_request_id")
RUN_ID = LogContextVar[int]("test_run_id")


class QuietConfigs(Configs):
    IS_PRINT_CONFIGS = BoolConfig(False)


class QuietSettings(Settings):
    configs = Slot(QuietConfigs)


class AuditLogging(Logging):
    """Adds a logger of its own, on the default handler."""

    def build_loggers(self) -> dict[str, dict[str, t.Any]]:
        audit = {"level": "WARNING", "handlers": ["default"], "propagate": False}
        return {**super().build_loggers(), "test_audit": audit}


class LoggingProject(Project):
    env_configs_prefix = "TEST"
    settings = Slot(QuietSettings)
    logging = Slot(AuditLogging)
