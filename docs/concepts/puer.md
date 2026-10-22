# PUER: projects, units, entities

Ingots is built around PUER, *Project-Unit-Entity-Runner*: an application is a
tree whose root is a **project**, whose branches are **units** and whose
leaves are **entities**; a **runner** drives the project. The tree is declared
on classes and composed by inheritance
([ADR 0004](https://github.com/ak-ingots/ingots-libs/blob/main/docs/adr/0004-static-composition-with-typed-slots.md)),
so mypy and the IDE see it as precisely as the code that runs.

## The roles

Project
: The root of the tree. In an application, the project *is* the application:
  everything it consists of hangs off it. In an addon, the project is the set
  of units the addon brings; an application combines addons by inheriting
  from their projects. Every unit and entity belongs to exactly one project,
  and several projects live in one process side by side without sharing
  anything.

Unit
: A namespace for the nested units and entities of one domain area: what an
  addon calls `auth`, `inventory` or `storage`. A unit groups, it does not do
  the work itself; it may nest other units to any depth.

Entity
: The workhorse: the object that does the work of the system - talks to a
  database, handles a request, computes a result. An entity reaches the rest
  of the system through its project.

Runner
: Drives a project: creates it, configures it, runs a workflow (a command,
  a server, ...), and shuts it down. It is the only long-lived holder of the project and drops it when
  done.

## Slots

A project or a unit declares its children as slots:
{py:class}`~ingots.puer.slots.Slot` descriptors on the class.

```python
from ingots.puer import Entity, Project, Slot, Unit


class Repository(Entity):
    def load(self) -> str: ...


class Storage(Unit):
    repository = Slot(Repository)


class StorageProject(Project):
    storage = Slot(Storage)
```

- **On the instance**, a slot is the child: `project.storage.repository` is a
  `Repository`, created on first access and kept by its owner. Nothing is
  created before it is used.
- **On the class**, a slot is the declaration: `StorageProject.storage` is the
  slot itself, and `StorageProject.storage.cls` the class it creates. The
  framework walks these declarations (to build a CLI, for example) without
  creating anything.
- A slot is never assigned: `project.storage = ...` raises `AttributeError`,
  and mypy rejects it.

A project or a unit is a {py:class}`~ingots.puer.slots.owner.SlotsOwner`: its
`slots_` methods walk its slots, all of them or those holding one kind of
entity, typed by that kind, and create nothing on the way.

- `StorageProject.slots_iter(Unit)` gives the names and the slots of the
  class itself; `StorageProject.slots_walk(Repository)` goes down through the
  units too, with dotted paths: `storage.repository`.
- `project.slots_find_entity("storage.repository", Repository)` gives the
  entity at a path, created with the units on the way; a path without a
  slot of that kind raises `LookupError` and creates nothing.
- `project.slots_walk_entities()` gives the entities created so far.

## Customization

A subclass customizes a child by declaring its slot again with a subclass of
the original class. A customization deep in the tree takes one short class
per level:

```python
class CachedRepository(Repository):
    def load(self) -> str:
        return f"cached {super().load()}"


class AppStorage(Storage):
    repository = Slot(CachedRepository)


class AppProject(StorageProject):
    storage = Slot(AppStorage)
```

`AppProject().storage.repository` is a `CachedRepository`, and mypy knows it.
An entity that needs more than its own addon's project narrows the type of its
back-reference with an annotation:

```python
class CachedRepository(Repository):
    project: "AppProject"  # the application's neighbours are visible and typed
```

## Combining addons

An application combines addons by inheriting from their projects:
`class AppProject(AuthProject, InventoryProject)`. Slots that only one addon
declares are inherited as they are. Where two addons extend the same default
(settings, typically) and so hold unrelated classes in one slot, the
application declares that slot with a class joining them:

```python
class AppSettings(AuthSettings, InventorySettings): ...


class AppProject(AuthProject, InventoryProject):
    settings = Slot(AppSettings)
```

The rule behind it is checked when a class is created, and mypy checks the
same: a slot of a subclass must hold a subclass of what every base holds in
it. Without the join, `AppProject` fails at import time with a `TypeError`
naming the slot and the bases, not in production.

## Lifetime

Entities hold their project through a weak reference: the tree has no
reference cycles, and a project dies as soon as its holder drops it.

- Someone must hold the project. `AppProject().storage.repository` fails with
  `ReferenceError`: the temporary project is gone before the second dot.
- An entity that outlives its project keeps its own state, but reaching for
  the project raises `ReferenceError`.
- `entity.project` is for immediate use. Kept in an attribute or a callback
  (`self.project.method` binds the project), it keeps the project alive.

## The runner

{py:class}`~ingots.puer.runner.BaseRunner` runs a project in three stages:

1. creates the project and configures it: awaits its `_configure()` hook;
2. runs the workflow, `_run_workflow()`, until it finishes or is stopped;
3. shuts the project down, whatever happened before, and drops the
   project.

It assumes nothing about where a run's input comes from: a subclass
implements the workflow, `_run_workflow()` and, to stop without being
cancelled, `_stop_workflow()`, and sets `_debug` and `_graceful_timeout` in
`_prepare_run()`. {doc}`cli` is one such runner.

## What to call, what to override

The framework keeps the flow of a project in its own hands and leaves the
details to its subclasses:

- **Final methods are called, not overridden**: `runner.run()`, the
  `slots_` methods. mypy rejects an override
  (`@typing.final`), so a forgotten `super()` cannot break them. The
  shutdown of a project is final too, and only the runner runs it.
- **Hooks are overridden, not called**: their names start with an
  underscore, and the framework calls them at their moment.
  `Project._configure()`, `Project._shut_down()`,
  `BaseRunner._run_workflow()`, `BaseCommand._run()` do the work of
  their class. They are empty
  or abstract in the framework: an override calls `super()` only to keep
  what its own bases do, an addon's project for example.
- An override says so with `@typing.override`. With mypy's
  `explicit-override` error code on, as in Ingots itself, a method that
  overrides a hook by chance, or a hook misspelt, is an error.
- Everything else with an underscore belongs to `ingots.puer` itself.

SIGINT and SIGTERM stop the run, from the configuring to the end of the
shutdown, and each further one insists more:

- the first calls `_stop_workflow()`, and cancels the workflow if it is still
  running after the graceful timeout (5 seconds by default); while
  configuring or shutting down, which cannot be asked to stop, it cancels
  them;
- the second cancels the current stage at once;
- the third kills the process with the signal, as if there were no runner,
  for a stage that does not even give in to cancelling.

A project whose configuring fails or is cancelled may be half set up, so it
is shut down all the same, without running the workflow. Shutting down that
is cancelled may leave resources behind, and the cancelling is logged.

The exit code is the workflow's, 1 when a stage fails or is cancelled; a
killed process reports the signal.
