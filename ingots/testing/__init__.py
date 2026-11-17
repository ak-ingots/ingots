"""
Testing a project: the project of a test case as a fixture, created and
configured for each test in its event loop, shut down after it.
"""

__all__ = ("FIXTURE_CONFIGS", "ProjectFixture", "ProjectTestCase")

from .fixtures import FIXTURE_CONFIGS, ProjectFixture, ProjectTestCase
