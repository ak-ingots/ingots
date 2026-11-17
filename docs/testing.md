# Testing

{py:mod}`ingots.testing` gives a test case its project as a fixture, created
for each test, configured by the test alone, and shut down after it.

## The project of a test case

A {py:class}`~ingots.testing.ProjectFixture` is declared on a
{py:class}`~ingots.testing.ProjectTestCase`, a
{py:class}`unittest.IsolatedAsyncioTestCase`, and read as the attribute it
is set to, typed by its project:

```python
from ingots.testing import ProjectFixture, ProjectTestCase


class CacheTestCase(ProjectTestCase):
    project = ProjectFixture(AppProject, configs={"REDIS_DEFAULT_PORT": "16380"})

    async def test_an_attempt_is_taken_once(self) -> None:
        cache = self.project.auth.cache
        ...
```

- Each test has a project of its own, created and configured in
  `asyncSetUp`, in the event loop of the test: a client a component opens
  is never of a closed loop. A cleanup shuts it down after the test,
  whatever the test raised, and after a configuring that failed too.
- The project is configured by its `configs`, as `--config` gives them,
  over {py:data}`~ingots.testing.FIXTURE_CONFIGS`; the environment of its
  prefix is hidden while it is configured, so the shell of the developer
  changes no test.
- {py:data}`~ingots.testing.FIXTURE_CONFIGS` turn `IS_PRINT_CONFIGS` off,
  and `IS_CONFIGURE_LOGGING` off: the logging of the process stays the
  one of the run, its loggers seen by `assertLogs`. A test of the logging
  itself turns it on in its `configs`.
- A test case has several fixtures, a server and its client: they are
  created in their order, those of the bases and mixins first, and shut
  down the other way round. A subclass declaring a fixture of the same name
  replaces it.
- A project is read while a test runs only: outside, a `RuntimeError`.

## Mixins and contracts

A mixin declares a fixture as a test case does; the test case taking it
joins it. The fixtures are created before the `asyncSetUp` of the bases
runs, so a contract of an addon (ADR 0005), whose own `asyncSetUp` asks
for its project, reads it there; {py:class}`~ingots.testing.ProjectTestCase`
comes last of the bases, standing for the test case of `unittest`:

```python
class ServerMixin:
    server = ProjectFixture(AppProject, configs={"REDIS_DEFAULT_PORT": "16380"})

    async def create_project(self) -> AuthProject:
        return self.server


class RedisSessionsCacheTestCase(
    ServerMixin, AuthSessionsCacheContract, ProjectTestCase
):
    pass
```
