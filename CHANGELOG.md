# Ingots Changelog

Ingots is rewritten from scratch starting with 0.30.0; versions up to 0.29.0
are the previous implementation.

<!-- towncrier release notes start -->

## [0.32.2] - 2026-10-28
### Added
- A command or a CLI unit names its sub-command with `cli_name`, taken from
  its slot when empty; two slots of a unit giving the same sub-command are
  refused with a `TypeError`.

## [0.32.1] - 2026-10-26
The changes of 0.32.0, on PyPI: the release of 0.32.0 stopped at the test of the package from TestPyPI, which holds it alone.

## [0.32.0] - 2026-10-26
### Added
- Added `Factory`, the slot of an entity for one use at a time: on the instance it is a `BoundFactory` creating a new entity on every call, `project.shop.pay()`, and giving its class as `cls`, owned by the caller, so the project neither walks nor shuts it down; a component or a unit takes a `Slot`. Both extend `BaseSlot`, which `slots_iter()` and `slots_walk()` now give; `slots_find_entity()` finds the entities of slots only.
- Added the operations of the defaults: a `BaseOperation`, typed by its parameters and its result, declares the `Permissions` it requires, the flags of their domains in a `PermissionFlags` (explicit bits, 31 per domain, for masks stored and sent between services), and runs in `_run()`; the unit of its domain declares it as a `Factory`. `project.operations.create_metadata(caller, run_uid=request_id)` prepares the `OperationMetadata` of a run, and `project.operations.runner.run(project.shop.pay, parameters, metadata)` runs a new instance with the uids of the run and of the caller in the log context; an operation runs others with the same metadata, as one run, and `run_safe()` gives `None` for one that fails, logging it. `operations.checker` lets a `Caller` run each or raises `OperationPermissionsError`; an exception of an operation is raised as it is.

### Changed
- A failed stage of the runner, a failed stop of the workflow and a component failing to shut down log the `repr()` of the exception in the message, its message and its context, `failed: RuntimeError('boom')`, before the traceback: the `str()` of an exception following the pattern of Ingots holds its message only.

## [0.31.0] - 2026-10-24
### Changed
- Joining units fails when the class is created instead of losing a source: settings must list in `LOADERS` the loaders of all their bases, and the formats of a file loader may not share an extension.

## [0.30.1] - 2026-10-22
### Fixed
- A project of the defaults reads its environment variables with the prefix `INGOT` unless it sets its own `env_configs_prefix`, instead of failing: an addon run on its own no longer repeats the prefix of the ecosystem.

## [0.30.0] - 2026-10-22
### Added
- Added `ingots.defaults` with its `Project` and the first standard unit, `settings`: typed, read-only configs in one flat namespace per project (`Configs`), extended by addons through slots, with configs for the built-in scalar types, dates and times, enums, logging levels and tuples. The values are applied once while the project is configured and printed when `IS_PRINT_CONFIGS` is on; `settings list` prints them on demand.
- Added the components: entities holding a resource, a server or a client, configured on first `await` and shut down with the project. A `Component` is an entity with a `SHUTDOWN_ORDER` and two hooks, `_configure()` and `_shut_down()`, in a plain slot; awaiting it, which is `@typing.final`, configures it once, through its project, which keeps the configured components. Shutting the project down shuts the configured components down by order, 1 to 9, and the project's `state` keeps any from being configured afterwards; components waiting for each other fail instead of hanging. The `components` unit of the defaults lists them (`components list`) and runs any of them until stopped (`components run-forever --component PATH`). `slots_find_path(entity)` gives the path of an entity under a project or a unit.
- Added the core of PUER in `ingots.puer`: `Project`, `Unit` and `Entity`, and `Slot`, a typed descriptor through which a project or a unit declares a child entity, created on first access and customized by declaring the slot again with a subclass (ADR 0004). Slot conflicts between bases are rejected when the class is created, a slot cannot be assigned on an instance, and entities hold their project through a weak reference.
- Added the hooks of the PUER flow: the framework keeps the flow in its hands, `runner.run()` and the `slots_` methods are `@typing.final`, and a subclass overrides the hooks, whose names start with an underscore. The runner awaits `Project._configure()`, runs the workflow and shuts the project down, which runs `Project._shut_down()`; neither needs `super()` for the framework. `BaseRunner` takes `_prepare_run()`, `_run_workflow()`, `_stop_workflow()` and `_create_project()`, `BaseCommand` takes `_run()` and `_stop()`, `CliNode` takes `_cli_prepare_parser()` and `_cli_build_args()`. Ingots checks its overrides with mypy's `explicit-override`, and the docs mark them with `@typing.override`.
- Added the logging of the defaults: `configure_startup_logging()` logs from the start of the process, then the `Logging` unit of `Project` configures the logging from the `LOGGING_*` configs of `Configs` once the settings are configured; `app logging info` prints the configuration. A `LogContextVar` puts a value bound in the context, a request id for example, into every log record. A `LogLevelConfig` prints the name of its level.
- Added the overrides of the settings: the configs are loaded from INI and JSON files (`--configs-file`), from the environment variables with the project's `env_configs_prefix` and from `--config NAME=value`, the later winning, then converted and applied in a second phase. A wrong override is logged and ignored, or, with `IS_STRICT_CONFIGS` on, fails the configuration with every problem at once. A source of another kind is a loader in a slot of `Settings`, listed in `Settings.LOADERS`. Joining the configs of addons fails when two of them declare one config name.
- Added the runner and the command line of PUER. `BaseRunner` runs a project in three stages - configures it, runs a workflow, shuts it down whatever happened - and drops it; each SIGINT/SIGTERM insists more: the first asks the workflow to stop and cancels it after the graceful timeout, the second cancels the current stage, the third kills the process. `ingots.puer.cli` builds the command line from the project's slots - `CliUnit` sub-commands and `BaseCommand` commands, each node adding its own options - through `CliParser`, which a runner may replace, and `CommandRunner` runs the chosen command, creating only the units on its path.
- Added the walks of the slots: projects and units walk their slots by the kind of entity, `slots_iter()`, `slots_walk()` with dotted paths, `slots_find_entity(path, kind)` and `slots_walk_entities()`. `Project.state`, a `ProjectState`, tells where the project is in its life: active, shutting down, shut down.
- Rewrote Ingots from scratch around static composition, with the development automation - `make check` (lint, tests on the working tree and on the built wheel for every supported Python, documentation build, changelog check), towncrier news fragments, the Sphinx documentation for Read the Docs and the `ci` workflow running the same targets.
