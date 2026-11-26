"""
The command line, a domain of its own: the unit ``cli`` of the project is its
root, the groups of commands of the domains its sub-commands.

A :class:`CommandsUnit` is a sub-command grouping the commands of its slots,
a :class:`BaseCommand` is what a runner runs, and :class:`CommandRunner`
runs the command chosen on the command line, creating only what lies on its
path. A command reaches the domain it serves through its project: the
domains hold no command.
"""

__all__ = (
    "BaseCommand",
    "CliNode",
    "CliParser",
    "CliTree",
    "CliUnit",
    "CommandRunner",
    "CommandRunnerCliArgs",
    "CommandsUnit",
    "ComponentsCommandsUnit",
    "ListComponentsCommand",
    "ListConfigsCommand",
    "LoggingCommandsUnit",
    "LoggingInfoCommand",
    "ParsedCommandLine",
    "ProjectCliArgs",
    "RunComponentsForeverCommand",
    "RunForeverCliArgs",
    "SettingsCommandsUnit",
)

import argparse
import typing as t
from dataclasses import dataclass
from pathlib import Path

from ingots.puer import Slot

from .command import BaseCommand
from .extensions.components import (
    ComponentsCommandsUnit,
    ListComponentsCommand,
    RunComponentsForeverCommand,
    RunForeverCliArgs,
)
from .extensions.logging import LoggingCommandsUnit, LoggingInfoCommand
from .extensions.settings import ListConfigsCommand, SettingsCommandsUnit
from .node import CliNode
from .parser import CliParser, CliTree, ParsedCommandLine
from .runner import CommandRunner, CommandRunnerCliArgs
from .unit import CommandsUnit


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCliArgs:
    """
    The overrides of the configs on the command line. Keyword-only, so the
    arguments of a subclass add fields of their own, with or without
    defaults.
    """

    configs: tuple[tuple[str, str], ...] = ()
    configs_files: tuple[Path, ...] = ()


class CliUnit(CommandsUnit):
    """
    The root of the command line, the unit ``cli`` of the project: the
    options of the project, ``--config`` and ``--configs-file``, read by the
    loaders of the settings, and the commands of the defaults, ``settings``,
    ``logging``, ``components``. An addon extends it with the group of its
    own, as it extends the settings::

        class AuthCliUnit(CliUnit):
            auth = Slot(AuthCommandsUnit)

    and an application taking several joins theirs in a class.
    """

    cli_args: ProjectCliArgs
    settings = Slot(SettingsCommandsUnit)
    logging = Slot(LoggingCommandsUnit)
    components = Slot(ComponentsCommandsUnit)

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
