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
: Drives a project: creates it, runs a command, and shuts it down. It is the
  only long-lived holder of the project. Not part of the core yet.

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
