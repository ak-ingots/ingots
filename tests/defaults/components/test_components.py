import contextlib
import io
import os
import typing as t
from unittest import mock

from ingots.puer import Component
from ingots.puer.cli import CommandRunner
from ingots.puer.components import is_configured

from tests import TestCase

from .components_fixtures import EVENTS, ComponentsProject


class ComponentsTestCase(TestCase):
    @t.override
    def setUp(self) -> None:
        EVENTS.clear()
        self.enterContext(mock.patch.dict(os.environ, {"TEST_IS_PRINT_CONFIGS": "off"}))
        # the logging is not under test: keep the handlers of assertLogs
        self.enterContext(mock.patch("logging.config.dictConfig"))

    def run_project(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = CommandRunner(ComponentsProject, argv).run()
        return code, out.getvalue()

    def test_the_list_prints_every_component(self) -> None:
        self.assertEqual(
            self.run_project("components", "list"),
            (
                0,
                "Components:\n"
                "http.server: Server, shutdown order 2\n"
                "http.client: Client, shutdown order 8\n"
                "admin: Admin, shutdown order 1\n"
                "------------\n",
            ),
        )

    def test_run_forever_runs_the_components_until_stopped(self) -> None:
        with self.assertLogs("ingots.defaults.components", "INFO") as logs:
            code, _ = self.run_project(
                "components", "run-forever", "--component", "http.server"
            )
        self.assertEqual(code, 0)
        self.assertEqual(EVENTS, ["listening", "closed"])
        self.assertEqual(
            logs.records[0].getMessage(), "running http.server until stopped"
        )

    def test_run_forever_takes_component_paths_only(self) -> None:
        with self.assertLogs("ingots.puer.runner", "ERROR") as logs:
            code, _ = self.run_project(
                "components", "run-forever", "--component", "http"
            )
        self.assertEqual(code, 1)
        self.assertIn("LookupError: no slot of Component at 'http'", logs.output[0])
        self.assertEqual(EVENTS, [])

    def test_a_component_is_found_by_its_path(self) -> None:
        project = ComponentsProject()
        component = project.slots_find_entity("admin", Component)
        self.assertIs(component, project.admin)
        self.assertFalse(is_configured(component))  # created, not configured
