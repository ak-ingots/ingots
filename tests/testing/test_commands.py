import contextlib
import importlib
import io
import os
import pathlib
import sys
import typing as t
import unittest
from unittest import mock

from ingots.defaults.cli import CommandRunner
from ingots.testing import OutsideRunError, RunTestsCommand, TestsFailedError
from ingots.testing.commands import get_package

from tests import TestCase

from .cases_fixtures import CacheProject

RUNS = pathlib.Path(__file__).parent / "runs"


class RunTestsTestCase(TestCase):
    @t.override
    def setUp(self) -> None:
        self.enterContext(mock.patch.dict(os.environ, clear=True))
        self.enterContext(mock.patch.object(sys, "path", [str(RUNS), *sys.path]))
        # the scenarios, out of the suite and of mypy: no package holds them
        self.play: t.Any = importlib.import_module("play")
        self.play.SEEN.clear()

    def run_tests(self, *options: str, **configs: str) -> tuple[int, str]:
        """``testing run`` with its options, the project with its configs."""
        argv = [
            *("--config", "IS_CONFIGURE_LOGGING=off"),
            *(arg for item in configs.items() for arg in ("--config", "=".join(item))),
            *("testing", "run", *options),
        ]
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = CommandRunner(self.play.PlayProject, argv).run()
        return code, err.getvalue()

    def test_the_scenarios_are_configured_as_the_command(self) -> None:
        os.environ["PLAY_PLAY_HOST"] = "game.local"
        code, _ = self.run_tests("-k", "game")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.play.SEEN,
            [
                {
                    "test": "game",
                    "host": "game.local",
                    "port": 50051,
                    "name": "scenario",  # the fixture wins
                    "is_configure_logging": False,  # the run keeps its logging
                }
            ],
        )
        self.assertIsNone(RunTestsCommand.get_run(self.play.PlayProject))

    def test_the_command_line_of_the_run_reaches_the_scenarios(self) -> None:
        with self.assertNoLogs("ingots.puer.runner"):
            code, _ = self.run_tests(PLAY_PORT="50061")
        self.assertEqual(code, 0)
        [game] = [seen for seen in self.play.SEEN if seen["test"] == "game"]
        self.assertEqual(game["port"], 50061)
        self.assertEqual(len(self.play.SEEN), 3)

    def test_a_failed_run_fails_the_command_by_its_count(self) -> None:
        with self.assertLogs("ingots.puer.runner", "ERROR") as logs:
            code, err = self.run_tests(PLAY_NAME="fail")
        self.assertEqual(code, 1)
        [record] = logs.records
        self.assertEqual(
            record.getMessage(), "the workflow failed: 1 of 3 tests failed"
        )
        self.assertIsNone(record.exc_info)
        self.assertIn("FAIL: test_fails_when_asked", err)

    def test_the_tests_are_named_as_unittest_names_them(self) -> None:
        code, err = self.run_tests("test_play.PlayScenario.test_the_second", "-v")
        self.assertEqual(code, 0)
        self.assertEqual(self.play.SEEN, [{"test": "second"}])
        self.assertIn("test_the_second", err)

    def test_the_run_stops_at_the_first_failure_when_asked(self) -> None:
        with self.assertLogs("ingots.puer.runner", "ERROR"):
            code, _ = self.run_tests("--failfast", PLAY_NAME="fail")
        self.assertEqual(code, 1)
        self.assertEqual(self.play.SEEN, [{"test": "failing"}])

    def test_a_scenario_outside_its_command_tells_the_command(self) -> None:
        test_play = importlib.import_module("play.test_play")
        result = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromTestCase(test_play.PlayScenario).run(
            result
        )
        self.assertEqual(len(result.errors), 2)
        self.assertIn(
            "OutsideRunError: run by: python -m play testing run", result.errors[0][1]
        )

    def test_the_errors_tell_their_parts(self) -> None:
        failed = TestsFailedError.for_counts(2, 5)
        self.assertEqual(
            (str(failed), failed.failed, failed.run), ("2 of 5 tests failed", 2, 5)
        )
        outside = OutsideRunError.for_package("play")
        self.assertEqual(outside.package, "play")

    def test_the_package_of_a_project_is_that_of_its_module(self) -> None:
        self.assertEqual(get_package(self.play.PlayProject).__name__, "play")
        self.assertEqual(get_package(CacheProject).__name__, "tests.testing")
