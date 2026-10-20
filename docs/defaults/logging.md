# The logging

The second unit of the defaults is `logging`: it configures the logging of
the process from the configs, once the {doc}`settings` are configured.

## The startup logging

Until then, the process logs with the startup logging: a thin wrapper over
{py:func}`logging.basicConfig`, called in the entry point before the runner.
It logs warnings and above by default; a lower level shows what happens at
the very start of the process, before any config is read:

```python
import sys

from ingots.defaults.logging import configure_startup_logging
from ingots.puer.cli import CommandRunner


def main() -> None:
    configure_startup_logging()  # logging.DEBUG to look into the start
    sys.exit(CommandRunner(AppProject).run())
```

## The configuration

The two units of the defaults are not independent: the settings declare the
configs of the logging, and the logging reads them through the project. An
application customizes the logging at two points: the configs, in its
configs class, and the parts of the configuration, in its logging unit.

Configuring the project configures the settings, then the
{py:class}`~ingots.defaults.logging.Logging` unit, which applies a
{py:func}`logging.config.dictConfig` built from the `LOGGING_*` configs of
{py:class}`~ingots.defaults.settings.configs.entity.Configs`:

- the `ingots` logger, at `LOGGING_INGOTS_LEVEL` (`INFO`), writes to the
  standard error in `LOGGING_INGOTS_FORMAT`, marked with `◈◈◈`, and does not
  propagate;
- with `LOGGING_ENABLE_ROOT_LOGGER` on, the root logger, at
  `LOGGING_ROOT_LOGGER_LEVEL` (`INFO`), writes to the standard error in
  `LOGGING_DEFAULT_FORMAT`; off (the default), it keeps the startup logging;
- `LOGGING_DISABLE_EXISTING_LOGGERS` passes `disable_existing_loggers`.

`app logging info` prints the configuration the project runs with. A
subclass of the unit extends a part of it, `build_formatters()`,
`build_filters()`, `build_handlers()` or `build_loggers()`, and takes the
slot of the project:

```python
class AuditLogging(Logging):
    def build_loggers(self) -> dict[str, dict[str, t.Any]]:
        audit = {"level": "WARNING", "handlers": ["default"], "propagate": False}
        return {**super().build_loggers(), "audit": audit}


class AppProject(Project):
    logging = Slot(AuditLogging)
```

The logging is global to the process: configuring a second project in it
replaces the logging of the first.

## The log context

An addon puts its context into the log records, a request id for example,
with a {py:class}`~ingots.defaults.logging.context.LogContextVar`: a context
variable declared once, at the module level, under a name prefixed with the
addon's. While a value is bound, both handlers add it to every record:

```python
from ingots.defaults.logging.context import LogContextVar

REQUEST_ID = LogContextVar[str]("http_request_id")


async def handle(request: Request) -> Response:
    with REQUEST_ID.bind(request.uid):
        logger.info("handled")  # ... ▶ http_request_id=a1b2
```

- The context is `%(cvars)s` in the formats: `name=value` pairs, `-` when
  nothing is bound. A handler of a subclass that formats it takes the
  `cvars` filter too.
- An asyncio task copies the context it is created in: a value bound in a
  task stays in that task.
- Declaring a name a second time is a `ValueError` at import, so two addons
  cannot share a name by accident.
