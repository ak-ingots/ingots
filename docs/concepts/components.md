# Components

A component is an entity holding a resource: a server, or a client of a
server or a store. Like every entity, it is created on first access to its
slot; unlike the others, it is configured asynchronously on first use and
shut down with the project.

## A component

A {py:class}`~ingots.puer.components.component.Component` is an entity with a
shutdown order and two hooks: `_configure()` takes the resource,
`_shut_down()` releases it. It takes a plain slot.

```python
import typing as t

from ingots.puer import Component, Slot, Unit


class Redis(Component):
    SHUTDOWN_ORDER = 8

    async def get(self, key: str) -> str:
        return await self._client.get(key)

    @t.override
    async def _configure(self) -> None:
        self._client = await connect(...)

    @t.override
    async def _shut_down(self) -> None:
        await self._client.close()


class Storage(Unit):
    redis = Slot(Redis)
```

Awaiting the component configures it, once, and gives it back:

```python
redis = await self.project.storage.redis
await redis.get("key")
```

- Every `await` goes through the project, which keeps the components it
  configured, those of its slots and any other, to shut them down.
- Concurrent awaits wait for the same configuration, which a cancelled
  caller does not cancel. After a failed configuration, the next `await`
  tries again.
- A component configures with others by awaiting them in `_configure()`.
  Components waiting for each other fail at once with a `RuntimeError`
  naming the loop by the paths of the components (`storage.cache →
  storage.redis → storage.cache`) instead of hanging.
- How a component lives between the two hooks (a client reconnecting, a
  server draining before it closes) is its own business, not the
  framework's.

The framework does not guard a component outside its life: that is the
component's business too.

- A component used without `await` is not configured: its methods run on
  what `_configure()` has not set yet, and fail as they happen to (an
  `AttributeError`, at best), or do not fail.
- A component used after the shutdown runs on what `_shut_down()` has
  released: a closed client, a stopped server.

## The shutdown

The runner shuts the project down, and the project the components it
configured, in their shutdown order: 1 to 9, 1 first; those of one order
together. A server takes a low order, to stop accepting before the clients
behind it close; a store client a high one. The order is `SHUTDOWN_ORDER`
of the component, 5 by default.

- A component that fails to shut down is logged; the others shut down all
  the same.
- A configuration still running is waited for first.
- The project moves from `ACTIVE` to `SHUTTING_DOWN` to `SHUT_DOWN`
  ({py:class}`~ingots.puer.constants.ProjectState`): from the shutdown on, no
  component is configured.
- A subclass of the project releasing more overrides `_shut_down()`, which
  runs before the components shut down; they shut down whatever it does.

## Customizing

A component is customized as any entity: a subclass, and the slot
declared again with it. The application caches what the addon reads, for
example:

```python
class CachedRedis(Redis):
    @t.override
    async def get(self, key: str) -> str: ...


class CachedStorage(Storage):
    redis = Slot(CachedRedis)
```

The slots of components are walked like any slots:
`AppProject.slots_walk(Component)` gives them with their paths.
