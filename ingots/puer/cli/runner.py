"""The command runner: runs the command chosen on the command line."""

__all__ = ("CommandRunner", "CommandRunnerCliArgs")

import argparse
import logging
import typing as t
from dataclasses import dataclass

from ingots.puer import BaseRunner

from .command import BaseCommand
from .node import CliNode
from .parser import CliParser, ParsedCommandLine

if t.TYPE_CHECKING:
    from collections.abc import Sequence

    from ingots.puer.project import Project

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CommandRunnerCliArgs:
    debug: bool = False
    graceful_timeout: float = BaseRunner.GRACEFUL_TIMEOUT_DEFAULT


class CommandRunner(CliNode, BaseRunner):
    """
    Builds the command line from the project's slots and runs the chosen
    command; a stop signal calls the command's :meth:`~BaseCommand.stop`.
    Only the units on the command's path are created, each with its CLI
    arguments.

    Usage, in the application's entry point::

        def main() -> None:
            sys.exit(CommandRunner(AppProject).run())

    The arguments are parsed from ``argv``, ``sys.argv[1:]`` by default, when
    the run starts.
    """

    cli_args: CommandRunnerCliArgs
    cli_parser_cls: t.ClassVar[type[CliParser]] = CliParser

    @staticmethod
    def _cli_check_graceful_timeout(value: str) -> float:
        try:
            timeout = float(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"not a number: {value!r}") from None
        if timeout <= 0:
            raise argparse.ArgumentTypeError(f"must be positive: {value!r}")
        return timeout

    @classmethod
    def cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--debug",
            dest="runner_debug",
            action="store_true",
            help="run the asyncio event loop in debug mode",
        )
        parser.add_argument(
            "--graceful-timeout",
            dest="runner_graceful_timeout",
            type=cls._cli_check_graceful_timeout,
            default=cls.GRACEFUL_TIMEOUT_DEFAULT,
            metavar="SECONDS",
            help=(
                "how long a stopped command may take to finish before it is "
                f"cancelled (default: {cls.GRACEFUL_TIMEOUT_DEFAULT})"
            ),
        )

    @classmethod
    def cli_build_args(cls, namespace: argparse.Namespace) -> CommandRunnerCliArgs:
        return CommandRunnerCliArgs(
            debug=namespace.runner_debug,
            graceful_timeout=namespace.runner_graceful_timeout,
        )

    def __init__(
        self, project_cls: type["Project"], argv: "Sequence[str] | None" = None
    ) -> None:
        super().__init__(project_cls)
        self._argv = argv
        self._command_line = ParsedCommandLine(None, (), {})
        self._command: BaseCommand | None = None

    def run(self) -> int:
        self._parse_args()
        return super().run()

    async def run_workflow(self) -> int:
        command = self._command = self._set_cli_args_on_path()
        logger.info("running %s", ".".join(self._command_line.command_path))
        try:
            await command.run()
        finally:
            self._command = None
        return 0

    async def stop_workflow(self) -> None:
        if self._command is not None:
            self._command.stop()

    def create_project(self) -> "Project":
        project = super().create_project()
        self._set_cli_args(project, ())
        return project

    def _parse_args(self) -> None:
        parser = self.cli_parser_cls(self._project_cls, type(self))
        self._command_line = parser.parse(self._argv)
        self._cli_set_args(self._command_line.runner_args)
        self._debug = self.cli_args.debug
        self._graceful_timeout = self.cli_args.graceful_timeout

    def _set_cli_args_on_path(self) -> BaseCommand:
        # every node on the command's path, down to the command at its end;
        # getting them through the slots creates them, and only them
        owner: object = self.project
        path = self._command_line.command_path
        for depth, name in enumerate(path, 1):
            owner = getattr(owner, name)
            self._set_cli_args(owner, path[:depth])
        assert isinstance(owner, BaseCommand), owner
        return owner

    def _set_cli_args(self, obj: object, path: tuple[str, ...]) -> None:
        if isinstance(obj, CliNode):
            obj._cli_set_args(self._command_line.node_args[path])
