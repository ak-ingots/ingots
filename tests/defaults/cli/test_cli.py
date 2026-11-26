import contextlib
import gc
import io
import typing as t
import unittest

from ingots.defaults.cli import (
    CliParser,
    CliTree,
    CommandRunner,
    CommandRunnerCliArgs,
    CommandsUnit,
    ProjectCliArgs,
)
from ingots.defaults.components import ComponentsUnit
from ingots.puer import Slot

from tests import TestCase

from .cli_fixtures import (
    EVENTS,
    PROJECTS,
    GreetCommand,
    GreetArgs,
    GreetingsUnit,
    GreetingsArgs,
    ShopCliUnit,
    ShopProject,
)


def list_tree(tree: CliTree, indent: str = "") -> list[str]:
    acc = []
    for child in tree.children:
        acc.append(f"{indent}{child.name} {'.'.join(child.path)}")
        acc.extend(list_tree(child, indent + "  "))
    return acc


class RunnerTestCase(TestCase):
    @t.override
    def setUp(self) -> None:
        EVENTS.clear()
        PROJECTS.clear()

    def run_shop(self, *argv: str) -> int:
        return CommandRunner(ShopProject, argv).run()


class CliTreeTestCase(unittest.TestCase):
    def test_the_tree_follows_the_slots_in_declaration_order(self) -> None:
        self.assertEqual(
            list_tree(CliParser(ShopProject, CommandRunner).tree),
            [
                "settings settings",
                "  list settings.list",
                "logging logging",
                "  info logging.info",
                "components components",
                "  list components.list",
                "  run-forever components.run_forever",
                "greetings greetings",
                "  greet greetings.greet",
                "server server",
                "  serve server.serve",
                "  run-stubborn server.run_stubborn",
                "fail fail",
            ],
        )

    def test_a_group_holds_only_commands_and_groups(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "Mixed.components: ComponentsUnit is not on the command line; a "
            "command reaches its domain through the project",
        ):

            class Mixed(CommandsUnit):
                components = Slot(ComponentsUnit)

    def test_the_help_lists_the_commands(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as exit:
            CommandRunner(ShopProject, ["--help"]).run()
        self.assertEqual(exit.exception.code, 0)
        self.assertIn("The shop.", out.getvalue())
        self.assertIn(
            "{settings,logging,components,greetings,server,fail}", out.getvalue()
        )
        self.assertIn("--graceful-timeout SECONDS", out.getvalue())

    def test_a_unit_help_shows_the_first_line_of_a_command_description(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            CommandRunner(ShopProject, ["greetings", "--help"]).run()
        self.assertRegex(out.getvalue(), r"greet +Greets someone\.\n")
        self.assertNotIn("Politely.", out.getvalue())

    def test_a_command_is_required(self) -> None:
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as exit,
        ):
            CommandRunner(ShopProject, ["greetings"]).run()
        self.assertEqual(exit.exception.code, 2)

    def test_a_runner_takes_its_own_parser(self) -> None:
        class SnakeCaseParser(CliParser):
            @t.override
            def _get_cli_name(self, slot_name: str) -> str:
                return slot_name

        class Runner(CommandRunner):
            cli_parser_cls = SnakeCaseParser

        server = SnakeCaseParser(ShopProject, Runner).tree.children[4]
        self.assertEqual(server.children[1].name, "run_stubborn")
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            Runner(ShopProject, ["server", "run-stubborn"]).run()


class FiniteCommandTestCase(RunnerTestCase):
    def test_a_command_runs_creating_only_the_units_on_its_path(self) -> None:
        self.assertEqual(self.run_shop("greetings", "greet", "--name", "Ann"), 0)
        self.assertEqual(
            EVENTS, ["configure", "hello Ann; created: _slot_greetings", "shut down"]
        )

    def test_every_node_on_the_path_gets_its_arguments(self) -> None:
        received: list[object] = []

        class Recorder(GreetCommand):
            @t.override
            async def _run(self) -> None:
                cli = self.project.cli
                received.extend([cli.cli_args, cli.greetings.cli_args, self.cli_args])

        class RecordingGreetings(GreetingsUnit):
            greet = Slot(Recorder)

        class RecordingCliUnit(ShopCliUnit):
            greetings = Slot(RecordingGreetings)

        class Project(ShopProject):
            cli = Slot(RecordingCliUnit)

        CommandRunner(Project, ["greetings", "--loud", "greet", "--name", "Bo"]).run()
        self.assertEqual(
            received, [ProjectCliArgs(), GreetingsArgs(loud=True), GreetArgs("Bo")]
        )

    def test_a_failing_command_exits_with_1_and_still_shuts_down(self) -> None:
        with self.assertLogs("ingots.puer.runner", "ERROR"):
            self.assertEqual(self.run_shop("fail"), 1)
        self.assertEqual(EVENTS, ["configure", "shut down"])


class StoppingTestCase(RunnerTestCase):
    def test_a_signal_asks_the_command_to_stop(self) -> None:
        self.assertEqual(self.run_shop("server", "serve"), 0)
        self.assertEqual(
            EVENTS, ["configure", "serving", "stop", "served", "shut down"]
        )

    def test_the_graceful_timeout_comes_from_the_command_line(self) -> None:
        with self.assertLogs("ingots.puer.runner", "WARNING"):
            code = self.run_shop("--graceful-timeout", "0.05", "server", "run-stubborn")
        self.assertEqual(code, 1)
        self.assertEqual(EVENTS, ["configure", "cancelled", "shut down"])


class RunnerArgsTestCase(RunnerTestCase):
    def test_the_runner_options(self) -> None:
        argv = ["--debug", "--graceful-timeout", "1.5", "greetings", "greet"]
        runner = CommandRunner(ShopProject, argv)
        runner.run()
        t.assert_type(runner.cli_args, CommandRunnerCliArgs)
        self.assertEqual(runner.cli_args, CommandRunnerCliArgs(True, 1.5))

    def test_the_graceful_timeout_must_be_positive(self) -> None:
        for value in ("0", "-1", "soon"):
            with (
                self.subTest(value=value),
                contextlib.redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                self.run_shop("--graceful-timeout", value, "fail")


class LifetimeTestCase(RunnerTestCase):
    def test_the_command_runner_drops_the_project_when_done(self) -> None:
        gc.disable()
        try:
            runner = CommandRunner(ShopProject, ["greetings", "greet"])
            runner.run()
            (ref,) = PROJECTS
            self.assertIsNone(ref(), "something keeps the project alive")
        finally:
            gc.enable()

    def test_a_node_off_the_command_path_has_no_cli_args(self) -> None:
        project = ShopProject()
        greet = project.cli.greetings.greet
        if t.TYPE_CHECKING:
            t.assert_type(greet.cli_args, GreetArgs)
        with self.assertRaisesRegex(RuntimeError, "not on the path"):
            greet.cli_args
