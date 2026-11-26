"""The command runner: runs the command chosen on the command line."""

__all__ = ("CommandRunner", "CommandRunnerCliArgs")

import argparse
import dataclasses
import logging
import typing as t
from dataclasses import dataclass

from ingots.puer import BaseRunner

from ingots.defaults.settings.configs import Configs

from .command import BaseCommand
from .data import ProjectCliArgs
from .node import CliNode
from .parser import CliParser, ParsedCommandLine

if t.TYPE_CHECKING:
    from collections.abc import Sequence

    from ingots.defaults.project import Project

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CommandRunnerCliArgs:
    debug: bool = False
    graceful_timeout: float = BaseRunner.GRACEFUL_TIMEOUT_DEFAULT


class CommandRunner(CliNode, BaseRunner):
    """
    Builds the command line from the unit ``cli`` of the project and runs
    the chosen command; a stop signal calls the command's
    :meth:`~BaseCommand.stop`. Only the groups on the command's path are
    created, each with its CLI arguments, the unit ``cli`` with the project.

    Usage, in the application's entry point::

        def main() -> None:
            sys.exit(CommandRunner(AppProject).run())

    The arguments are parsed from ``argv``, ``sys.argv[1:]`` by default, when
    the run starts.
    """

    cli_args: CommandRunnerCliArgs
    cli_parser_cls: t.ClassVar[type[CliParser]] = CliParser
    _project_cls: type["Project"]

    @staticmethod
    def _cli_check_graceful_timeout(value: str) -> float:
        try:
            timeout = float(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"not a number: {value!r}") from None
        if timeout <= 0:
            raise argparse.ArgumentTypeError(f"must be positive: {value!r}")
        return timeout

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
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

    @t.override
    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> CommandRunnerCliArgs:
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

    @t.override
    async def _run_workflow(self) -> int:
        command = self._command = self._set_cli_args_on_path(self._get_project())
        logger.info("running %s", ".".join(self._command_line.command_path))
        try:
            await command._run()
        finally:
            self._command = None
        return 0

    @t.override
    async def _stop_workflow(self) -> None:
        if self._command is not None:
            self._command._stop()

    @t.override
    def _create_project(self) -> "Project":
        project = self._project_cls()
        self._set_cli_args(project.cli, ())
        return project

    @t.override
    def _prepare_run(self) -> None:
        parser = self.cli_parser_cls(self._project_cls, type(self))
        self._command_line = parser.parse(self._argv)
        command_cls = parser.find_node(self._command_line.command_path).cls
        if issubclass(command_cls, BaseCommand) and command_cls.cli_is_quiet:
            self._command_line = self._quiet(self._command_line)
        self._cli_set_args(self._command_line.runner_args)
        self._debug = self.cli_args.debug
        self._graceful_timeout = self.cli_args.graceful_timeout

    def _quiet(self, command_line: ParsedCommandLine) -> ParsedCommandLine:
        # an override of the command line before those given, which win
        args = command_line.node_args[()]
        if not isinstance(args, ProjectCliArgs):
            return command_line
        off = (Configs.IS_PRINT_CONFIGS.name, "off")
        node_args = {
            **command_line.node_args,
            (): dataclasses.replace(args, configs=(off, *args.configs)),
        }
        return dataclasses.replace(command_line, node_args=node_args)

    def _get_project(self) -> "Project":
        project = self.project
        assert isinstance(project, self._project_cls)
        return project

    def _set_cli_args_on_path(self, project: "Project") -> BaseCommand:
        # every node on the command's path, down to the command at its end;
        # getting them through the slots creates them, and only them
        owner: CliNode = project.cli
        path = self._command_line.command_path
        for depth, name in enumerate(path, 1):
            owner = getattr(owner, name)
            self._set_cli_args(owner, path[:depth])
        assert isinstance(owner, BaseCommand), owner
        return owner

    def _set_cli_args(self, node: CliNode, path: tuple[str, ...]) -> None:
        node._cli_set_args(self._command_line.node_args[path])
