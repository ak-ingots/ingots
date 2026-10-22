"""A store client and a server as components, recording their lifecycle."""

import asyncio
import typing as t

from ingots.puer import Component, Project, Slot, Unit

EVENTS: list[str] = []


class Store(Component):
    SHUTDOWN_ORDER = 8

    @property
    def label(self) -> str:
        return type(self).__qualname__

    async def get(self, key: str) -> str:
        return self._data[key]

    @t.override
    async def _configure(self) -> None:
        await asyncio.sleep(0)
        EVENTS.append(f"configure {self.label}")
        self._data = {"key": "value"}

    @t.override
    async def _shut_down(self) -> None:
        EVENTS.append(f"shut down {self.label}")
        self._data.clear()


class CachedStore(Store):
    SHUTDOWN_ORDER = 3


class Server(Component):
    SHUTDOWN_ORDER = 1
    project: "ComponentsProject"

    @t.override
    async def _configure(self) -> None:
        await self.project.storage.store  # the server needs the store
        EVENTS.append("configure server")

    @t.override
    async def _shut_down(self) -> None:
        EVENTS.append("shut down server")


class Storage(Unit):
    store = Slot(Store)
    cache = Slot(CachedStore)


class ComponentsProject(Project):
    storage = Slot(Storage)
    server = Slot(Server)


class FlakyServer(Server):
    """Fails its first configuration and every shutdown."""

    @t.override
    async def _configure(self) -> None:
        self._attempts = getattr(self, "_attempts", 0) + 1
        if self._attempts == 1:
            raise ConnectionError("the port is taken")

    @t.override
    async def _shut_down(self) -> None:
        raise ConnectionError("the socket is gone")


class FlakyProject(ComponentsProject):
    server = Slot(FlakyServer)


class Loop(Component):
    """Waits for the other half of the loop."""

    project: "LoopProject"

    @t.override
    async def _configure(self) -> None:
        project = self.project
        await (project.second if self is project.first else project.first)


class LoopProject(Project):
    first = Slot(Loop)
    second = Slot(Loop)
