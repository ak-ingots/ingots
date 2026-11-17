"""The project of a test case: a fixture, one project for each test."""

__all__ = ("FIXTURE_CONFIGS", "ProjectFixture", "ProjectTestCase")

import contextlib
import os
import types
import typing as t
import unittest

from ingots.defaults import Project, ProjectCliArgs

if t.TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

# what every project of a test is configured with, its own configs winning:
# its configs not printed, the logging of the process left to the run
FIXTURE_CONFIGS: "Mapping[str, str]" = types.MappingProxyType(
    {"IS_PRINT_CONFIGS": "off", "IS_CONFIGURE_LOGGING": "off"}
)


class ProjectFixture[ProjectType: Project]:
    """
    The project of a test case, read as the attribute the fixture is set
    to: created and configured for each test in its event loop, shut down
    after it, so that no component outlives the loop it was created in.

    The project is configured by :data:`FIXTURE_CONFIGS`, then ``configs``,
    as ``--config`` gives them, never by the environment of its prefix,
    hidden while it is configured::

        class CacheTestCase(ProjectTestCase):
            project = ProjectFixture(AppProject, configs={"HTTP_PORT": "18080"})

            async def test_serves(self) -> None:
                server = await self.project.http.servers.default
    """

    def __init__(
        self, cls: type[ProjectType], *, configs: "Mapping[str, str]" = {}
    ) -> None:
        self.cls = cls
        self.configs: "Mapping[str, str]" = types.MappingProxyType(dict(configs))

    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...

    # any owner: a mixin declares a fixture too, a test case joins it
    @t.overload
    def __get__(self, obj: object, owner: type) -> ProjectType: ...

    def __get__(self, obj: object, owner: type) -> "t.Self | ProjectType":
        """
        The project of the running test.

        :raises RuntimeError: no test is running.
        """
        if obj is None:
            return self
        try:
            projects = t.cast(ProjectTestCase, obj)._fixtures_projects
            return t.cast(ProjectType, projects[self])
        except AttributeError, KeyError:
            raise RuntimeError(
                f"{type(obj).__qualname__}: the project of a fixture "
                "exists while a test runs only"
            ) from None

    async def create(self, case: unittest.IsolatedAsyncioTestCase) -> ProjectType:
        """
        A configured project, shut down by a cleanup of ``case``: added
        before the project is configured, so a failed configuring releases
        what it got.
        """
        project = self.cls()
        case.addAsyncCleanup(project._do_shut_down)
        configs = {**FIXTURE_CONFIGS, **self.configs}
        project._cli_set_args(ProjectCliArgs(configs=tuple(configs.items())))
        with hide_env(project.env_configs_prefix):
            await project._configure()
        return project


class ProjectTestCase(unittest.IsolatedAsyncioTestCase):
    """
    A test case of the projects of its fixtures, of its class, its bases and
    its mixins: each test creates them in their order, the bases first, and
    shuts them down after it, the later first. They are created before the
    ``asyncSetUp`` of the bases runs, so that every base reads them there,
    whatever its place in the order of the classes.
    """

    _fixtures: t.ClassVar[tuple[ProjectFixture[t.Any], ...]] = ()
    _fixtures_projects: dict[ProjectFixture[t.Any], Project]

    @t.override
    @classmethod
    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        # by name, so that a subclass declaring one again replaces it
        fixtures: dict[str, ProjectFixture[t.Any]] = {}
        for base in reversed(cls.__mro__):
            for name, value in vars(base).items():
                if isinstance(value, ProjectFixture):
                    fixtures[name] = value
        cls._fixtures = tuple(fixtures.values())

    @t.override
    async def asyncSetUp(self) -> None:
        self._fixtures_projects = {}
        self.addCleanup(self._fixtures_projects.clear)
        for fixture in self._fixtures:
            self._fixtures_projects[fixture] = await fixture.create(self)
        await super().asyncSetUp()


@contextlib.contextmanager
def hide_env(prefix: str) -> "Iterator[None]":
    """The environment without the variables of ``prefix``, restored after."""
    prefix = f"{prefix}_".upper()
    hidden = {
        name: value
        for name, value in os.environ.items()
        if name.upper().startswith(prefix)
    }
    for name in hidden:
        del os.environ[name]
    try:
        yield
    finally:
        os.environ.update(hidden)
