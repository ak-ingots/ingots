"""An addon with configs of its own, and an application joining two addons."""

import argparse
import enum
import typing as t
from dataclasses import dataclass

from ingots.defaults import Project, ProjectCliArgs
from ingots.defaults.settings import Settings
from ingots.defaults.settings.loaders import BaseLoader, Overrides
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
    env_configs_prefix = "TEST"
    settings = Slot(HttpSettings)


class DbConfigs(Configs):
    DB_NAME = StrConfig("app")
    DB_MODE = EnumConfig(Mode.SAFE)


class DbSettings(Settings):
    configs = Slot(DbConfigs)


class DbProject(Project):
    env_configs_prefix = "TEST"
    settings = Slot(DbSettings)


class AppConfigs(HttpConfigs, DbConfigs):
    pass


class AppSettings(HttpSettings, DbSettings):
    configs = Slot(AppConfigs)


class AppProject(HttpProject, DbProject):
    settings = Slot(AppSettings)


class VaultLoader(BaseLoader):
    """A source of another kind: a secrets store."""

    @t.override
    async def load(self) -> list[Overrides]:
        return [Overrides("the vault", {"HTTP_TOKEN": "from the vault"})]


class VaultSettings(AppSettings):
    LOADERS = (*AppSettings.LOADERS, "vault_loader")
    vault_loader = Slot(VaultLoader)


class VaultProject(AppProject):
    settings = Slot(VaultSettings)


class StrictConfigs(AppConfigs):
    IS_STRICT_CONFIGS = BoolConfig(True)


class StrictSettings(AppSettings):
    configs = Slot(StrictConfigs)


class StrictProject(AppProject):
    settings = Slot(StrictSettings)


@dataclass(frozen=True, slots=True, kw_only=True)
class VerboseCliArgs(ProjectCliArgs):
    verbose: bool


class VerboseProject(AppProject):
    """Adds an option of its own to those of the defaults."""

    cli_args: VerboseCliArgs

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        super()._cli_prepare_parser(parser)
        parser.add_argument("--verbose", dest="verbose", action="store_true")

    @t.override
    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> VerboseCliArgs:
        base = super()._cli_build_args(namespace)
        return VerboseCliArgs(
            configs=base.configs,
            configs_files=base.configs_files,
            verbose=namespace.verbose,
        )


class DefaultPrefixProject(Project):
    """Keeps the prefix of the defaults for its environment variables."""
