# Out of the default project

Every addon starts from the {py:class}`~ingots.defaults.project.Project` of
the defaults, and from the same few classes on top of it. Its settings and
its logging are not two independent units: the settings declare the configs
of the logging, the logging reads them through the project. So an addon
customizes both at two points, its configs and its logging unit, and adds
the units of its own domain next to them.

## The starting point

An HTTP addon, `ingot-http`, imported as `ingot_http`:

```python
"""An HTTP addon: the project an application inherits from."""

import asyncio
import logging
import sys
import typing as t

from ingots.defaults import Project
from ingots.defaults.logging import Logging, configure_startup_logging
from ingots.defaults.settings import Settings
from ingots.defaults.settings.configs import (
    Configs,
    IntConfig,
    LogLevelConfig,
    StrConfig,
)
from ingots.puer import Slot
from ingots.puer.cli import BaseCommand, CliUnit, CommandRunner

logger = logging.getLogger(__name__)


class HttpConfigs(Configs):
    HTTP_HOST = StrConfig("127.0.0.1")
    HTTP_PORT = IntConfig(8080)
    HTTP_LOGGING_LEVEL = LogLevelConfig(logging.INFO)


class HttpSettings(Settings):
    configs = Slot(HttpConfigs)


class HttpLogging(Logging):
    project: "HttpProject"

    def build_loggers(self) -> dict[str, dict[str, t.Any]]:
        level = self.project.settings.configs.HTTP_LOGGING_LEVEL
        http = {"level": level, "handlers": ["default"], "propagate": False}
        return {**super().build_loggers(), __name__: http}


class ServeCommand(BaseCommand):
    cli_description = "Serves HTTP until stopped."
    project: "HttpProject"

    def __init__(self, project: "HttpProject") -> None:
        super().__init__(project)
        self._stopped = asyncio.Event()

    async def run(self) -> None:
        configs = self.project.settings.configs
        logger.info("serving on %s:%s", configs.HTTP_HOST, configs.HTTP_PORT)
        await self._stopped.wait()

    def stop(self) -> None:
        self._stopped.set()


class Http(CliUnit):
    cli_description = "The HTTP server."
    serve = Slot(ServeCommand)


class HttpProject(Project):
    env_configs_prefix = "INGOT"
    settings = Slot(HttpSettings)
    logging = Slot(HttpLogging)
    http = Slot(Http)


def main() -> None:
    configure_startup_logging()
    sys.exit(CommandRunner(HttpProject).run())
```

Level by level:

- **The configs.** `HttpConfigs` extends the configs of the defaults with
  those of the domain, prefixed with the name of the domain, not of the
  package (`HTTP_*`, as `MYSQL_*` or `REDIS_*`), the logging configs of
  the domain among them: `HTTP_LOGGING_LEVEL`. `HttpSettings` narrows the slot
  of the settings to them; see {doc}`settings`.
- **The logging.** `HttpLogging` adds the addon's logger to the
  configuration, read from its configs; formatters, filters and handlers
  are extended the same way, each part calling `super()`. Its `project`
  annotation narrows the back-reference, so the configs of the domain are
  typed. See {doc}`logging`.
- **The domain.** `Http` is a unit of the addon's own, with its commands;
  every entity reaches the configs through the project.
- **The project.** `HttpProject` takes the three slots. It is what an
  application inherits from, and runs the addon on its own: the
  environment prefix `INGOT` and `main()` serve that run, an application
  sets its own (`APP_HTTP_PORT`).
- **The entry point.** `configure_startup_logging()` logs from the very
  start, before the settings are read; pass `logging.DEBUG` to look into
  it.

```console
$ INGOT_HTTP_PORT=9090 python -m ingot_http --config HTTP_LOGGING_LEVEL=debug http serve
Configs:
...
2026-10-20 06:13:02,440 ▶ INFO ▶ serving on 127.0.0.1:9090 ▶ ingot_http:52 ▶ Task-3 ▶ -
```

A value of the addon's context, a request id for example, goes into its
log records through a
{py:class}`~ingots.defaults.logging.context.LogContextVar`, declared next
to the logger: see {doc}`logging`.

## An application of two addons

An application joining two such addons joins the three slots that both
extend, one short class each; the parts of the logging configuration of
both addons meet through `super()`:

```python
class AppConfigs(HttpConfigs, DbConfigs): ...


class AppSettings(HttpSettings, DbSettings):
    configs = Slot(AppConfigs)


class AppLogging(HttpLogging, DbLogging): ...


class AppProject(HttpProject, DbProject):
    env_configs_prefix = "APP"
    settings = Slot(AppSettings)
    logging = Slot(AppLogging)
```

A slot that only one addon declares, `http`, is inherited as it is.
Forgetting a join fails at import time with a `TypeError` naming the slot;
two addons declaring one config name fail the same way.
