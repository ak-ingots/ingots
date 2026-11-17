"""A project of tests and the test cases run by the tests of the fixtures."""

import asyncio
import typing as t
import unittest

from ingots.defaults import Project
from ingots.defaults.settings import SettingsUnit
from ingots.defaults.settings.configs import Configs, StrConfig
from ingots.puer import Slot
from ingots.testing import ProjectFixture, ProjectTestCase

# what the test cases saw: the names of the projects shut down, in order,
# and the projects and loops of the tests
SHUT_DOWN: list[str] = []
SEEN: list[tuple["CacheProject", asyncio.AbstractEventLoop]] = []


class CacheConfigs(Configs):
    CACHE_NAME = StrConfig("cache")
    CACHE_HOST = StrConfig("localhost")


class CacheSettingsUnit(SettingsUnit):
    configs = Slot(CacheConfigs)


class CacheProject(Project):
    env_configs_prefix = "TEST"
    settings = Slot(CacheSettingsUnit)
    loop: asyncio.AbstractEventLoop

    @t.override
    async def _configure(self) -> None:
        await super()._configure()
        self.loop = asyncio.get_running_loop()

    @t.override
    async def _shut_down(self) -> None:
        SHUT_DOWN.append(self.settings.configs.CACHE_NAME)
        await super()._shut_down()


class LoopsTestCase(ProjectTestCase):
    project = ProjectFixture(CacheProject)

    async def test_first(self) -> None:
        SEEN.append((self.project, asyncio.get_running_loop()))

    async def test_second(self) -> None:
        SEEN.append((self.project, asyncio.get_running_loop()))


class ContractTestCase(unittest.IsolatedAsyncioTestCase):
    """A base reading its project in its own setup: a contract of an addon."""

    async def create_project(self) -> CacheProject:
        raise NotImplementedError

    @t.override
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.contract_project = await self.create_project()


class ServerMixin:
    """A fixture of a mixin, joined by the test cases taking it."""

    server = ProjectFixture(CacheProject, configs={"CACHE_NAME": "server"})

    async def create_project(self) -> CacheProject:
        return self.server


class TwoProjectsTestCase(ServerMixin, ContractTestCase, ProjectTestCase):
    client = ProjectFixture(CacheProject, configs={"CACHE_NAME": "client"})

    async def test_both(self) -> None:
        assert self.contract_project is self.server
        SHUT_DOWN.append("test")


class RenamedServerTestCase(TwoProjectsTestCase):
    server = ProjectFixture(CacheProject, configs={"CACHE_NAME": "renamed"})


class WrongConfigTestCase(ProjectTestCase):
    project = ProjectFixture(
        CacheProject,
        configs={"CACHE_NAME": "wrong", "IS_STRICT_CONFIGS": "on", "CACHE_PORT": "1"},
    )

    async def test_never_runs(self) -> None:
        raise AssertionError("the project is configured")
