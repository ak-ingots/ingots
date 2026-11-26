"""
A shop driven from the command line: commands that finish, one that runs
until stopped, one that ignores stopping, one that fails, and a group with no
command, left off.
"""

import argparse
import asyncio
import os
import signal
import typing as t
import weakref
from dataclasses import dataclass

from ingots.defaults import Project
from ingots.defaults.cli import BaseCommand, CliUnit, CommandsUnit
from ingots.puer import Slot

# what happened during a run: the project is gone when the run returns
EVENTS: list[str] = []
PROJECTS: list[weakref.ref["ShopProject"]] = []


@dataclass(frozen=True)
class GreetArgs:
    name: str


class GreetCommand(BaseCommand):
    cli_description = "Greets someone.\n\nPolitely."
    cli_args: GreetArgs
    project: "ShopProject"

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--name", dest="greet_name", default="world")

    @t.override
    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> GreetArgs:
        return GreetArgs(namespace.greet_name)

    @t.override
    async def _run(self) -> None:
        cli = vars(self.project.cli)
        created = sorted(k for k in cli if k.startswith("_slot_"))
        EVENTS.append(f"hello {self.cli_args.name}; created: {', '.join(created)}")


@dataclass(frozen=True)
class GreetingsArgs:
    loud: bool


class GreetingsUnit(CommandsUnit):
    cli_description = "GreetingsUnit."
    cli_args: GreetingsArgs
    greet = Slot(GreetCommand)

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--loud", dest="greetings_loud", action="store_true")

    @t.override
    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> GreetingsArgs:
        return GreetingsArgs(namespace.greetings_loud)


class ServeCommand(BaseCommand):
    """Runs until stopped: sends itself SIGINT once it is serving."""

    cli_description = "Serves forever."

    @t.override
    async def _run(self) -> None:
        self._stopped = asyncio.Event()
        EVENTS.append("serving")
        asyncio.get_running_loop().call_soon(os.kill, os.getpid(), signal.SIGINT)
        await self._stopped.wait()
        EVENTS.append("served")

    @t.override
    def _stop(self) -> None:
        EVENTS.append("stop")
        self._stopped.set()


class StubbornCommand(BaseCommand):
    """Ignores stopping: the runner has to cancel it."""

    @t.override
    async def _run(self) -> None:
        asyncio.get_running_loop().call_soon(os.kill, os.getpid(), signal.SIGTERM)
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            EVENTS.append("cancelled")
            raise


class ServerUnit(CommandsUnit):
    serve = Slot(ServeCommand)
    run_stubborn = Slot(StubbornCommand)


class FailCommand(BaseCommand):
    @t.override
    async def _run(self) -> None:
        raise RuntimeError("boom")


class EmptyUnit(CommandsUnit):
    """A group without commands: left out of the command line."""


class ShopCliUnit(CliUnit):
    cli_description = "The shop."
    greetings = Slot(GreetingsUnit)
    server = Slot(ServerUnit)
    fail = Slot(FailCommand)
    empty = Slot(EmptyUnit)


class ShopProject(Project):
    cli = Slot(ShopCliUnit)

    @t.override
    async def _configure(self) -> None:
        PROJECTS.append(weakref.ref(self))
        EVENTS.append("configure")

    @t.override
    async def _shut_down(self) -> None:
        EVENTS.append("shut down")
