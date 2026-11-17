import contextlib
import io
import os
import typing as t
import unittest
from unittest import mock

from ingots.puer.constants import ProjectState
from ingots.testing import FIXTURE_CONFIGS, ProjectFixture, ProjectTestCase

from tests import TestCase

# the module, not its test cases: they run by the tests here, not by discovery
from . import cases_fixtures as fixtures
from .cases_fixtures import SEEN, SHUT_DOWN, CacheProject


class ProjectFixtureTestCase(TestCase):
    @t.override
    def setUp(self) -> None:
        self.enterContext(mock.patch.dict(os.environ, clear=True))
        SHUT_DOWN.clear()
        SEEN.clear()

    def run_case(self, case: type[unittest.TestCase]) -> unittest.TestResult:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(case)
        result = unittest.TestResult()
        suite.run(result)
        return result

    def test_each_test_has_a_project_of_its_loop_shut_down_after(self) -> None:
        result = self.run_case(fixtures.LoopsTestCase)
        self.assertTrue(result.wasSuccessful(), result.errors)
        (first, first_loop), (second, second_loop) = SEEN
        self.assertIsNot(first, second)
        self.assertIs(first.loop, first_loop)
        self.assertIs(second.loop, second_loop)
        self.assertIsNot(first_loop, second_loop)
        self.assertIs(first.state, ProjectState.SHUT_DOWN)
        self.assertIs(second.state, ProjectState.SHUT_DOWN)

    def test_the_environment_of_the_prefix_is_hidden(self) -> None:
        os.environ.update({"TEST_CACHE_NAME": "shell", "TEST_CACHE_HOST": "shell"})
        self.run_case(fixtures.LoopsTestCase)
        (project, _), _ = SEEN
        self.assertEqual(project.settings.configs.CACHE_NAME, "cache")
        self.assertEqual(project.settings.configs.CACHE_HOST, "localhost")
        self.assertEqual(os.environ["TEST_CACHE_NAME"], "shell")

    def test_the_project_is_quiet_and_leaves_the_logging_alone(self) -> None:
        out = io.StringIO()
        with (
            contextlib.redirect_stdout(out),
            mock.patch("logging.config.dictConfig") as dict_config,
        ):
            self.run_case(fixtures.LoopsTestCase)
        self.assertEqual(out.getvalue(), "")
        dict_config.assert_not_called()
        self.assertEqual(
            dict(FIXTURE_CONFIGS),
            {"IS_PRINT_CONFIGS": "off", "IS_CONFIGURE_LOGGING": "off"},
        )

    def test_the_fixtures_of_the_mixins_come_first_and_shut_down_last(self) -> None:
        result = self.run_case(fixtures.TwoProjectsTestCase)
        self.assertTrue(result.wasSuccessful(), result.errors)
        self.assertEqual(SHUT_DOWN, ["test", "client", "server"])

    def test_a_subclass_replaces_a_fixture_by_its_name(self) -> None:
        self.run_case(fixtures.RenamedServerTestCase)
        self.assertEqual(SHUT_DOWN, ["test", "client", "renamed"])
        self.assertEqual(len(fixtures.RenamedServerTestCase._fixtures), 2)

    def test_a_project_failing_to_configure_is_shut_down(self) -> None:
        with self.assertLogs("ingots.defaults.settings", "ERROR"):
            result = self.run_case(fixtures.WrongConfigTestCase)
        [(_, error)] = result.errors
        self.assertIn("ConfigsError", error)
        self.assertEqual(SHUT_DOWN, ["cache"])  # the configs never applied

    def test_a_project_is_read_while_a_test_runs_only(self) -> None:
        self.assertIsInstance(fixtures.LoopsTestCase.project, ProjectFixture)
        case = fixtures.LoopsTestCase("test_first")
        with self.assertRaisesRegex(RuntimeError, "while a test runs only"):
            case.project
        case.run(unittest.TestResult())
        with self.assertRaisesRegex(RuntimeError, "LoopsTestCase: the project"):
            case.project

    def test_a_fixture_is_typed_by_its_project(self) -> None:
        class TypedTestCase(ProjectTestCase):
            project = ProjectFixture(CacheProject, configs={"CACHE_NAME": "typed"})

            async def test_typed(self) -> None:
                t.assert_type(self.project, CacheProject)
                SHUT_DOWN.append(self.project.settings.configs.CACHE_NAME)

        self.assertTrue(self.run_case(TypedTestCase).wasSuccessful())
        self.assertEqual(SHUT_DOWN, ["typed", "typed"])
