"""The project of the defaults."""

__all__ = ("Project", "ProjectCliArgs")

import argparse
import typing as t
from dataclasses import dataclass
from pathlib import Path

from ingots.puer import Slot
from ingots.puer.cli import CliProject

from .components import Components
from .logging import Logging
from .settings import Settings


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCliArgs:
    """
    The overrides of the configs on the command line. Keyword-only, so the
    arguments of a subclass add fields of their own, with or without
    defaults.
    """

    configs: tuple[tuple[str, str], ...] = ()
    configs_files: tuple[Path, ...] = ()


class Project(CliProject):
    """
    The project an application starts from: a command-line project with the
    standard units. Configuring it configures the units in their order:
    the settings, then the logging from the configs; shutting it down shuts
    down the components it configured.

    An application sets :attr:`env_configs_prefix`: ``"APP"`` reads
    ``APP_HTTP_PORT`` for the config ``HTTP_PORT``.
    """

    env_configs_prefix: t.ClassVar[str]

    cli_args: ProjectCliArgs
    settings = Slot(Settings)
    logging = Slot(Logging)
    components = Slot(Components)

    @staticmethod
    def _cli_check_config(option: str) -> tuple[str, str]:
        name, equals, data = option.partition("=")
        if not (name and equals):
            raise argparse.ArgumentTypeError(f"{option!r} is not NAME=value")
        return name, data

    @staticmethod
    def _cli_check_configs_file(option: str) -> Path:
        path = Path(option)
        if not path.is_file():
            raise argparse.ArgumentTypeError(f"{option!r} is not a file")
        return path

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--config",
            dest="project_configs",
            action="append",
            default=[],
            type=cls._cli_check_config,
            metavar="NAME=value",
            help="overrides a config; repeat for more",
        )
        parser.add_argument(
            "--configs-file",
            dest="project_configs_files",
            action="append",
            default=[],
            type=cls._cli_check_configs_file,
            metavar="PATH",
            help="overrides configs from an INI or JSON file; repeat for more",
        )

    @t.override
    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> ProjectCliArgs:
        return ProjectCliArgs(
            configs=tuple(namespace.project_configs),
            configs_files=tuple(namespace.project_configs_files),
        )

    @t.override
    async def _configure(self) -> None:
        await super()._configure()
        await self.settings.configure()
        await self.logging.configure()
