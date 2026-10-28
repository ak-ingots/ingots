import contextlib
import gc
import io
import typing as t
import unittest

from ingots.puer.cli import (
    BaseCommand,
    CliNode,
    CliParser,
    CliProject,
    CliTree,
    CliUnit,
    CommandRunner,
    CommandRunnerCliArgs,
)

from ingots.puer import Slot

from tests import TestCase

from .cli_fixtures import (
    EVENTS,
    PROJECTS,
    Greet,
    GreetArgs,
    Greetings,
    GreetingsArgs,
    NoCommandsProject,
    PlainProject,
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
                "greetings greetings",
                "  greet greetings.greet",
                "server server",
                "  serve server.serve",
                "  run-stubborn server.run_stubborn",
                "fail fail",
            ],
        )

    def test_a_class_names_its_sub_command(self) -> None:
        class Get(BaseCommand):
            cli_name = "get"

            @t.override
            async def _run(self) -> None:
                pass

        class Tags(CliUnit):
            cli_name = "labels"
            cmd_get = Slot(Get)

        class TagsProject(ShopProject):
            unit_tags = Slot(Tags)

        tree = CliParser(TagsProject, CommandRunner).tree
        self.assertEqual(
            list_tree(tree)[-2:], ["labels unit_tags", "  get unit_tags.cmd_get"]
        )

    def test_two_slots_giving_one_sub_command_are_refused(self) -> None:
        class Get(BaseCommand):
            cli_name = "get"

            @t.override
            async def _run(self) -> None:
                pass

        class Tags(CliUnit):
            get = Slot(Get)
            cmd_get = Slot(Get)

        class TagsProject(CliProject):
            tags = Slot(Tags)

        with self.assertRaisesRegex(
            TypeError, "Tags: the slots get and cmd_get give the same sub-command 'get'"
        ):
            CliParser(TagsProject, CommandRunner)

    def test_the_help_lists_the_commands(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as exit:
            CommandRunner(ShopProject, ["--help"]).run()
        self.assertEqual(exit.exception.code, 0)
        self.assertIn("The shop.", out.getvalue())
        self.assertIn("{greetings,server,fail}", out.getvalue())
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
            def _get_cli_name(self, slot_name: str, cls: type[CliNode]) -> str:
                return slot_name

        class Runner(CommandRunner):
            cli_parser_cls = SnakeCaseParser

        server = SnakeCaseParser(ShopProject, Runner).tree.children[1]
        self.assertEqual(server.children[1].name, "run_stubborn")
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            Runner(ShopProject, ["server", "run-stubborn"]).run()

    def test_a_project_without_commands_is_refused(self) -> None:
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as exit:
            CommandRunner(NoCommandsProject, []).run()
        self.assertEqual(exit.exception.code, 2)
        self.assertIn("the project declares no commands", err.getvalue())


class FiniteCommandTestCase(RunnerTestCase):
    def test_a_command_runs_creating_only_the_units_on_its_path(self) -> None:
        self.assertEqual(self.run_shop("greetings", "greet", "--name", "Ann"), 0)
        self.assertEqual(
            EVENTS, ["configure", "hello Ann; created: _slot_greetings", "shut down"]
        )

    def test_every_node_on_the_path_gets_its_arguments(self) -> None:
        received: list[object] = []

        class Recorder(Greet):
            @t.override
            async def _run(self) -> None:
                project = self.project
                received.extend(
                    [project.cli_args, project.greetings.cli_args, self.cli_args]
                )

        class RecordingGreetings(Greetings):
            greet = Slot(Recorder)

        class Project(ShopProject):
            greetings = Slot(RecordingGreetings)

        CommandRunner(Project, ["greetings", "--loud", "greet", "--name", "Bo"]).run()
        self.assertEqual(received, [None, GreetingsArgs(loud=True), GreetArgs("Bo")])

    def test_a_plain_project_runs_the_commands_of_its_cli_units(self) -> None:
        self.assertEqual(CommandRunner(PlainProject, ["greetings", "greet"]).run(), 0)
        self.assertEqual(EVENTS, ["hello world; created: _slot_greetings"])

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
        greet = project.greetings.greet
        if t.TYPE_CHECKING:
            t.assert_type(greet.cli_args, GreetArgs)
        with self.assertRaisesRegex(RuntimeError, "not on the path"):
            greet.cli_args
