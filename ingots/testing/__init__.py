"""
Testing a project: the project of a test case as a fixture, created and
configured for each test in its event loop, shut down after it; a project
whose tests run by its own command, ``testing run``, configured as it is.
"""

__all__ = (
    "FIXTURE_CONFIGS",
    "OutsideRunError",
    "ProjectFixture",
    "ProjectTestCase",
    "RunTestsCliArgs",
    "RunTestsCommand",
    "TestingProject",
    "TestingUnit",
    "TestsFailedError",
)

from .commands import RunTestsCliArgs, RunTestsCommand
from .errors import OutsideRunError, TestsFailedError
from .fixtures import FIXTURE_CONFIGS, ProjectFixture, ProjectTestCase
from .project import TestingProject, TestingUnit
