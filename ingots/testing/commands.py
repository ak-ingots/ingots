"""The command of the tests of a project."""

__all__ = ("RunTestsCliArgs", "RunTestsCommand")

import argparse
import asyncio
import importlib
import sys
import types
import typing as t
import unittest
from dataclasses import dataclass
from pathlib import Path

from ingots.defaults import Project
from ingots.defaults.cli import BaseCommand, ProjectCliArgs

from .errors import TestsFailedError


@dataclass(frozen=True, slots=True, kw_only=True)
class RunTestsCliArgs:
    """The options of unittest the command takes."""

    names: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()
    verbosity: int = 1
    failfast: bool = False


class RunTestsCommand(BaseCommand):
    """
    ``python -m app testing run``: runs the tests of the package of the
    project, the package of the module declaring its class, ``test*.py`` in
    it and its subpackages or those named, in a thread of their own, as
    each test case runs its own event loop. The fixtures of the class of
    the project are configured as the command is, by the environment and
    the command line, while it runs.
    """

    cli_description = "Runs the tests of the project, configured as it is."
    cli_args: RunTestsCliArgs
    project: Project

    # the arguments of each project class while its tests run
    _runs: t.ClassVar[dict[type[Project], ProjectCliArgs]] = {}

    @classmethod
    def get_run(cls, project_cls: type[Project]) -> ProjectCliArgs | None:
        """The arguments of the run of the tests of a project class, if any."""
        return cls._runs.get(project_cls)

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "run_tests_names",
            nargs="*",
            metavar="NAME",
            help="a test module, case or method, as unittest names it; all "
            "by default",
        )
        parser.add_argument(
            "-k",
            dest="run_tests_patterns",
            action="append",
            default=[],
            metavar="PATTERN",
            help="runs the tests matching the pattern, as unittest -k; repeat "
            "for more",
        )
        parser.add_argument(
            "-v",
            dest="run_tests_verbosity",
            action="store_const",
            const=2,
            default=1,
            help="prints each test as it runs",
        )
        parser.add_argument(
            "--failfast",
            dest="run_tests_failfast",
            action="store_true",
            help="stops at the first failure",
        )

    @t.override
    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> RunTestsCliArgs:
        return RunTestsCliArgs(
            names=tuple(namespace.run_tests_names),
            patterns=tuple(namespace.run_tests_patterns),
            verbosity=namespace.run_tests_verbosity,
            failfast=namespace.run_tests_failfast,
        )

    @t.override
    async def _run(self) -> None:
        project_cls = type(self.project)
        self._runs[project_cls] = self.project.cli.cli_args
        try:
            result = await asyncio.to_thread(self._run_tests)
        finally:
            del self._runs[project_cls]
        if not result.wasSuccessful():
            failed = len(result.failures) + len(result.errors)
            raise TestsFailedError.for_counts(failed, result.testsRun)

    def _run_tests(self) -> unittest.TestResult:
        args = self.cli_args
        loader = unittest.TestLoader()
        loader.testNamePatterns = [
            pattern if "*" in pattern else f"*{pattern}*" for pattern in args.patterns
        ] or None
        package = get_package(type(self.project))
        if args.names:
            suite = loader.loadTestsFromNames(
                [f"{package.__name__}.{name}" for name in args.names]
            )
        else:
            start = Path(t.cast(str, package.__file__)).parent
            top = start.parents[package.__name__.count(".")]
            suite = loader.discover(str(start), top_level_dir=str(top))
        runner = unittest.TextTestRunner(
            stream=sys.stderr, verbosity=args.verbosity, failfast=args.failfast
        )
        return runner.run(suite)


def get_package(project_cls: type[Project]) -> types.ModuleType:
    """The package of the module declaring a project class, or the module."""
    module = sys.modules[project_cls.__module__]
    if hasattr(module, "__path__"):
        return module
    return importlib.import_module(module.__name__.rpartition(".")[0])
