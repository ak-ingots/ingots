# The settings

The first unit of the defaults is `settings`: the configs of the project
and what serves them.

## Configs

A config is a typed descriptor with a default. All the configs of a project
share one flat namespace, a
{py:class}`~ingots.defaults.settings.configs.entity.Configs` entity, so an addon
prefixes its configs with its name. The base class holds the configs of the
defaults themselves: those of the settings and the `LOGGING_*` of
{doc}`logging`. An addon adds its configs with three short classes, one per
level:

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
- Joining configs checks the names when the class is created: two unrelated
  bases declaring one name is a clash of two addons, an error. The
  application declaring a config sets its own default, which is never a
  clash: the joining class is the top of the MRO. A base that overrides a
  config of a common ancestor wins over it without a clash too.
- The values live in the configs entity, not in the descriptors: two
  projects in one process have their own.

## Read-only configs

The configs are written once. Configuring the
{py:class}`~ingots.defaults.settings.Settings` unit applies the overrides
loaded for them and freezes them; from then on the configs are what the
project started with, and what it printed.

- Assigning a config is an error for mypy and an `AttributeError` at run
  time.
- `Configs.apply()` checks every value before it sets any, and is called
  once.
- When `IS_PRINT_CONFIGS` is on (the default), configuring prints every
  config with its value, sorted by name; `app settings list` prints them on
  demand.

## Overrides

Configuring the settings runs in two phases.

1. The loaders of `Settings.LOADERS` collect the overrides of their
   sources: names to data as the source has it, a string or a JSON value.
   They apply in this order, the later winning:
   - `--configs-file PATH`, an INI file (the options of every section) or a
     JSON object, repeated for more files;
   - the environment variables with the project's prefix: with
     `env_configs_prefix = "APP"` on the project, `APP_HTTP_PORT=9090`;
   - `--config NAME=value`, repeated for more configs.
2. The settings convert the overrides to the values of the configs and
   apply them.

A wrong override is an unknown name, data that does not convert or a source
that cannot be read. By default it is logged and ignored, and the config
keeps its default. With `IS_STRICT_CONFIGS` on, every wrong override is
collected and the configuration fails with all of them, so the process does
not start. The mode is a config too: the default of the configs class, or
an override from any source (`--config IS_STRICT_CONFIGS=on`). Data for the
mode itself that does not convert counts as strict.

Every problem is logged, a warning when ignored and an error when strict;
the {py:class}`~ingots.defaults.settings.ConfigsError` keeps them in
`problems`:

```console
$ APP_IS_STRICT_CONFIGS=1 app --config HTTP_PORT=x serve
the command line: HTTP_PORT: 'x' is not an int
configuring failed
Traceback (most recent call last):
  ...
ingots.defaults.settings.ConfigsError: 1 wrong override of the configs
```

A source of another kind, a secrets store for example, is a loader in a
slot of the settings, added to `LOADERS`:

```python
class VaultLoader(BaseLoader):
    async def load(self) -> list[Overrides]:
        return [Overrides("the vault", await read_secrets())]


class VaultSettings(Settings):
    LOADERS = (*Settings.LOADERS, "vault_loader")
    vault_loader = Slot(VaultLoader)
```

A file format is a slot of the
{py:class}`~ingots.defaults.settings.loaders.files.FileLoader`, chosen by the
`EXTENSIONS` it declares. YAML, for example, with PyYAML:

```python
import yaml

from ingots.defaults.settings.loaders import BaseFormat, FileLoader


class YamlFormat(BaseFormat):
    EXTENSIONS = frozenset({".yaml", ".yml"})

    def parse(self, text: str) -> dict[str, object]:
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as error:
            raise ValueError(str(error)) from None
        if not isinstance(data, dict):
            raise ValueError("not a YAML mapping")
        return data


class YamlFileLoader(FileLoader):
    yaml_format = Slot(YamlFormat)


class YamlSettings(Settings):
    file_loader = Slot(YamlFileLoader)
```

`app --configs-file app.yaml` then reads it; a `ValueError` from `parse()`
is a problem of the file, as for the built-in formats.
