# The settings

The first unit of the defaults is `settings`: the configs of the project
and what serves them.

## Configs

A config is a typed descriptor with a default. All the configs of a project
share one flat namespace, a
{py:class}`~ingots.defaults.settings.configs.entity.Configs` entity, so an addon
prefixes its configs with its name. An addon adds its configs with three
short classes, one per level:

```python
from ingots.defaults import Project
from ingots.defaults.settings import Settings
from ingots.defaults.settings.configs import Configs, IntConfig, SecureStrConfig
from ingots.puer import Slot


class HttpConfigs(Configs):
    HTTP_PORT = IntConfig(8080)
    HTTP_TOKEN = SecureStrConfig("")


class HttpSettings(Settings):
    configs = Slot(HttpConfigs)


class HttpProject(Project):
    settings = Slot(HttpSettings)
```

and reads them through the project: `self.project.settings.configs.HTTP_PORT`
is an `int` for mypy. An application with two such addons joins them
explicitly, as every slot (ADR 0004):

```python
class AppConfigs(HttpConfigs, DbConfigs): ...


class AppSettings(HttpSettings, DbSettings):
    configs = Slot(AppConfigs)


class AppProject(HttpProject, DbProject):
    settings = Slot(AppSettings)
```

- The types: `BoolConfig`, `IntConfig`, `FloatConfig`, `DecimalConfig`,
  `StrConfig`, `SecureStrConfig` (printed as `***`), `DateConfig`,
  `TimeConfig`, `DateTimeConfig` (ISO 8601), `EnumConfig` (by member name),
  `LogLevelConfig` (by level name) and `TupleConfig` (shaped as its default,
  a JSON array in a string). A config of another type extends
  {py:class}`~ingots.defaults.settings.configs.base.BaseConfig`: `validate()` checks a
  value, `_parse()` converts the data of a source.
- A default is checked when the class is created; a subclass of the configs
  overrides a default by declaring the config again, of the same type.
- The values live in the configs entity, not in the descriptors: two
  projects in one process have their own.

## Read-only configs

The configs are written once. Configuring the
{py:class}`~ingots.defaults.settings.Settings` unit applies the values
loaded for them (`load_values()`) and freezes them; from then on the
configs are what the project started with, and what it printed.

- Assigning a config is an error for mypy and an `AttributeError` at run
  time.
- `Configs.apply()` checks every value before it sets any, and is called
  once.
- When `IS_PRINT_CONFIGS` is on (the default), configuring prints every
  config with its value, sorted by name; `app settings list` prints them on
  demand.
