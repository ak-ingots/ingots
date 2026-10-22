"""A project with a server that stops the run once listening, and a client."""

import asyncio
import os
import signal
import typing as t

from ingots.defaults import Project
from ingots.puer import Component, Slot, Unit

EVENTS: list[str] = []


class Server(Component):
    """Listens, then sends SIGINT to the process: the run stops."""

    SHUTDOWN_ORDER = 2

    @t.override
    async def _configure(self) -> None:
        EVENTS.append("listening")
        asyncio.get_running_loop().call_soon(os.kill, os.getpid(), signal.SIGINT)

    @t.override
    async def _shut_down(self) -> None:
        EVENTS.append("closed")


class Admin(Server):
    SHUTDOWN_ORDER = 1


class Client(Component):
    SHUTDOWN_ORDER = 8


class Http(Unit):
    server = Slot(Server)
    client = Slot(Client)


class ComponentsProject(Project):
    env_configs_prefix = "TEST"
    http = Slot(Http)
    admin = Slot(Admin)
