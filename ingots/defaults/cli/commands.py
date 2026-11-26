"""The commands of the command line itself: ``completion bash``."""

__all__ = ("BashCompletionCliArgs", "BashCompletionCommand", "CompletionCommandsUnit")

import argparse
import os
import typing as t
from dataclasses import dataclass

from ingots.puer import Slot

from .command import BaseCommand
from .completion import BashCompletion, CompletionKind, CompletionTarget
from .runner import CommandRunner
from .unit import CommandsUnit

if t.TYPE_CHECKING:
    from ingots.defaults.project import Project


@dataclass(frozen=True, slots=True, kw_only=True)
class BashCompletionCliArgs:
    target: CompletionTarget


class BashCompletionCommand(BaseCommand):
    """
    ``completion bash``: prints the script of the completion of the program
    run, as it is run, or of the one named: ``--command shop``, ``--script
    manage.py``, ``--module shop``. Installed once, a console script in
    ``~/.local/share/bash-completion/completions/<name>``, a script or a
    module in a file that ``~/.bashrc`` sources.
    """

    cli_is_quiet = True
    cli_description = "Prints the script of the completion of bash."
    cli_args: BashCompletionCliArgs
    project: "Project"

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--command",
            dest="completion_command",
            metavar="NAME",
            help="a console script, by its name",
        )
        group.add_argument(
            "--script",
            dest="completion_script",
            metavar="PATH",
            help="a script run by python, by its path",
        )
        group.add_argument(
            "--module",
            dest="completion_module",
            metavar="NAME",
            help="a module run by python -m, by its name",
        )

    @t.override
    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> BashCompletionCliArgs:
        if namespace.completion_command:
            target = CompletionTarget(
                kind=CompletionKind.COMMAND, name=namespace.completion_command
            )
        elif namespace.completion_script:
            target = CompletionTarget(
                kind=CompletionKind.SCRIPT,
                name=os.path.realpath(namespace.completion_script),
            )
        elif namespace.completion_module:
            target = CompletionTarget(
                kind=CompletionKind.MODULE, name=namespace.completion_module
            )
        else:
            target = CompletionTarget.from_argv()
        return BashCompletionCliArgs(target=target)

    @t.override
    async def _run(self) -> None:
        completion = BashCompletion(
            type(self.project), CommandRunner, self.cli_args.target
        )
        print(completion.build(), end="")


class CompletionCommandsUnit(CommandsUnit):
    """``completion``: the completion of the command line by a shell."""

    cli_description = "The completion of the command line by a shell."
    bash = Slot(BashCompletionCommand)
