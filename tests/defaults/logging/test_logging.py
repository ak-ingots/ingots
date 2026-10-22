import asyncio
import contextlib
import io
import logging
import os
import typing as t
from unittest import mock

from ingots.defaults import ProjectCliArgs
from ingots.defaults.logging import configure_startup_logging
from ingots.defaults.logging.context import LogContextFilter
from ingots.defaults.logging.startup import STARTUP_LOGGING_FORMAT
from ingots.puer.cli import CommandRunner

from tests import TestCase

from .logging_fixtures import REQUEST_ID, LoggingProject


class StartupLoggingTestCase(TestCase):
    def test_the_startup_logging_logs_warnings_by_default(self) -> None:
        configure_startup_logging()
        self.assertEqual(logging.root.level, logging.WARNING)
        [handler] = logging.root.handlers
        self.assertIsInstance(handler.formatter, logging.Formatter)
        assert handler.formatter is not None
        self.assertEqual(handler.formatter._fmt, STARTUP_LOGGING_FORMAT)

    def test_the_startup_level_is_set_in_place(self) -> None:
        configure_startup_logging(logging.DEBUG)
        configure_startup_logging("INFO")  # replaces the first
        self.assertEqual(logging.root.level, logging.INFO)
        self.assertEqual(len(logging.root.handlers), 1)


class LoggingTestCase(TestCase):
    @t.override
    def setUp(self) -> None:
        self.enterContext(mock.patch.dict(os.environ, clear=True))

    def create_project(self) -> LoggingProject:
        project = LoggingProject()
        project._cli_set_args(ProjectCliArgs())
        return project

    def test_the_configuration_is_built_from_the_configs(self) -> None:
        project = self.create_project()
        asyncio.run(project.settings.configure())
        configs = project.settings.configs
        config = project.logging.build_config()
        self.assertEqual(
            config["formatters"],
            {
                "default": {"format": configs.LOGGING_DEFAULT_FORMAT},
                "ingots": {"format": configs.LOGGING_INGOTS_FORMAT},
            },
        )
        self.assertEqual(config["filters"], {"cvars": {"()": LogContextFilter}})
        self.assertEqual(
            config["handlers"]["ingots"],
            {
                "class": "logging.StreamHandler",
                "formatter": "ingots",
                "filters": ["cvars"],
            },
        )
        self.assertEqual(
            config["loggers"]["ingots"],
            {"level": logging.INFO, "handlers": ["ingots"], "propagate": False},
        )
        self.assertIn("test_audit", config["loggers"])
        self.assertFalse(config["disable_existing_loggers"])
        self.assertNotIn("root", config)

    def test_the_root_logger_is_configured_when_enabled(self) -> None:
        os.environ.update(
            {
                "TEST_LOGGING_ENABLE_ROOT_LOGGER": "on",
                "TEST_LOGGING_ROOT_LOGGER_LEVEL": "debug",
            }
        )
        project = self.create_project()
        asyncio.run(project.settings.configure())
        self.assertEqual(
            project.logging.build_config()["root"],
            {"level": logging.DEBUG, "handlers": ["default"]},
        )

    def test_configuring_logs_with_the_log_context(self) -> None:
        project = self.create_project()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            asyncio.run(project._configure())
            with REQUEST_ID.bind("a1"):
                logging.getLogger("ingots.test").info("handled")
            logging.getLogger("test_audit").warning("audited")
            logging.getLogger("test_audit").info("dropped")
        ingots_line, audit_line = err.getvalue().splitlines()
        self.assertRegex(
            ingots_line,
            r"^◈◈◈ \S+ \S+ ▶ INFO ▶ handled ▶ ingots\.test:\d+ ▶ \S+ "
            r"▶ test_request_id=a1$",
        )
        self.assertRegex(
            audit_line, r"^\S+ \S+ ▶ WARNING ▶ audited ▶ test_audit:\d+ ▶ \S+ ▶ -$"
        )

    def test_the_info_command_prints_the_configuration(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(
                CommandRunner(LoggingProject, ["logging", "info"]).run(), 0
            )
        printed = out.getvalue()
        self.assertTrue(printed.startswith("Logging:\n    version: 1\n"))
        self.assertIn(
            "\n    loggers:\n        ingots:\n            level: 20\n", printed
        )
        self.assertIn("\n        test_audit:\n", printed)
        self.assertTrue(printed.endswith("\n------------\n"))
