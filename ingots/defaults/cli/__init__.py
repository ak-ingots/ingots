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
    "BashCompletion",
    "BashCompletionCliArgs",
    "BashCompletionCommand",
    "CliCompletion",
    "CliNode",
    "CliParser",
    "CliTree",
    "CliUnit",
    "CommandRunner",
    "CommandRunnerCliArgs",
    "CommandsUnit",
    "CompletionCommandsUnit",
    "CompletionKind",
    "CompletionTarget",
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
from pathlib import Path

if t.TYPE_CHECKING:
    from ingots.defaults.project import Project

from ingots.defaults.settings.configs import iter_configs
from ingots.puer import Slot

from .command import BaseCommand
from .commands import (
    BashCompletionCliArgs,
    BashCompletionCommand,
    CompletionCommandsUnit,
)
from .completion import BashCompletion, CompletionKind, CompletionTarget
from .data import CliCompletion, ProjectCliArgs
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


class CliUnit(CommandsUnit):
    """
    The root of the command line, the unit ``cli`` of the project: the
    options of the project, ``--config`` and ``--configs-file``, read by the
    loaders of the settings, and the commands of the defaults, ``settings``,
    ``logging``, ``components``, and the command line's own,
    ``completion``. An addon extends it with the group of its own, as it
    extends the settings::

        class AuthCliUnit(CliUnit):
            auth = Slot(AuthCommandsUnit)

    and an application taking several joins theirs in a class.
    """

    cli_args: ProjectCliArgs
    settings = Slot(SettingsCommandsUnit)
    logging = Slot(LoggingCommandsUnit)
    components = Slot(ComponentsCommandsUnit)
    completion = Slot(CompletionCommandsUnit)

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
    def _cli_complete(cls, project_cls: "type[Project]", dest: str) -> CliCompletion:
        if dest == "project_configs":
            configs_cls = project_cls.settings.cls.configs.cls
            names = tuple(f"{config.name}=" for config in iter_configs(configs_cls))
            return CliCompletion(words=names, is_spaced=False)
        if dest == "project_configs_files":
            return CliCompletion(files=True)
        return super()._cli_complete(project_cls, dest)

    @t.override
    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> ProjectCliArgs:
        return ProjectCliArgs(
            configs=tuple(namespace.project_configs),
            configs_files=tuple(namespace.project_configs_files),
        )
