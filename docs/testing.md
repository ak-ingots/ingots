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

## The tests of an application

The scenarios of an application, a client of it run against it, are a
project of their own, a {py:class}`~ingots.testing.TestingProject`: its
command `testing run` runs the tests of its package, configured as any
project is, by the environment of its prefix, `--config` and
`--configs-file`; the fixtures of its class take what the command took,
their own configs winning:

```python
class ScenariosCliUnit(TestingCliUnit, GrpcCliUnit): ...


class ScenariosProject(TestingProject, GrpcProject):
    env_configs_prefix = "GAME_TEST"
    settings = Slot(ScenariosSettingsUnit)
    grpc = Slot(ScenariosGrpcUnit)  # a client of the application
    cli = Slot(ScenariosCliUnit)  # testing and the commands of the addon


class SignUpScenario(ProjectTestCase):
    project = ProjectFixture(ScenariosProject)
```

```console
$ GAME_TEST_GRPC_DEFAULT_PORT=50061 python -m scenarios testing run -k sign_up -v
```

- `testing run` takes the options of unittest: the tests by their names,
  `test_play.PlayScenario`, relative to the package; `-k` patterns; `-v`;
  `--failfast`. A failed run exits with 1, the count of the failures
  logged, no traceback: unittest told them above.
- The tests run in a thread of their own: each test case runs its own
  event loop, not the one of the command.
- A fixture of a `TestingProject` outside its command raises
  {py:class}`~ingots.testing.OutsideRunError`, telling the command:
  `python -m unittest` would configure it with the defaults and fail far
  from the cause.
- The logging of the process is the command's: the project of the command
  configures it, the projects of the scenarios do not.
