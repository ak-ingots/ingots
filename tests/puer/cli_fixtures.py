"""
A shop driven from the command line: commands that finish, one that runs
until stopped, one that ignores stopping, one that fails, and units that stay
off the command line.
"""

import argparse
import asyncio
import os
import signal
import weakref
from dataclasses import dataclass

from ingots.puer import Project, Slot, Unit
from ingots.puer.cli import BaseCommand, CliProject, CliUnit

# what happened during a run: the project is gone when the run returns
EVENTS: list[str] = []
PROJECTS: list[weakref.ref["ShopProject"]] = []


@dataclass(frozen=True)
class GreetArgs:
    name: str


class Greet(BaseCommand):
    cli_description = "Greets someone.\n\nPolitely."
    cli_args: GreetArgs
    project: "ShopProject"

    @classmethod
    def cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--name", dest="greet_name", default="world")

    @classmethod
    def cli_build_args(cls, namespace: argparse.Namespace) -> GreetArgs:
        return GreetArgs(namespace.greet_name)

    async def run(self) -> None:
        created = sorted(k for k in vars(self.project) if k.startswith("_slot_"))
        EVENTS.append(f"hello {self.cli_args.name}; created: {', '.join(created)}")


@dataclass(frozen=True)
class GreetingsArgs:
    loud: bool


class Greetings(CliUnit):
    cli_description = "Greetings."
    cli_args: GreetingsArgs
    greet = Slot(Greet)

    @classmethod
    def cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--loud", dest="greetings_loud", action="store_true")

    @classmethod
    def cli_build_args(cls, namespace: argparse.Namespace) -> GreetingsArgs:
        return GreetingsArgs(namespace.greetings_loud)


class Serve(BaseCommand):
    """Runs until stopped: sends itself SIGINT once it is serving."""

    cli_description = "Serves forever."

    async def run(self) -> None:
        self._stopped = asyncio.Event()
        EVENTS.append("serving")
        asyncio.get_running_loop().call_soon(os.kill, os.getpid(), signal.SIGINT)
        await self._stopped.wait()
        EVENTS.append("served")

    def stop(self) -> None:
        EVENTS.append("stop")
        self._stopped.set()


class Stubborn(BaseCommand):
    """Ignores stopping: the runner has to cancel it."""

    async def run(self) -> None:
        asyncio.get_running_loop().call_soon(os.kill, os.getpid(), signal.SIGTERM)
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            EVENTS.append("cancelled")
            raise


class Server(CliUnit):
    serve = Slot(Serve)
    run_stubborn = Slot(Stubborn)


class Fail(BaseCommand):
    async def run(self) -> None:
        raise RuntimeError("boom")


class Hidden(Unit):
    """Not a CLI unit: its command stays off the command line."""

    greet = Slot(Greet)


class Empty(CliUnit):
    """A CLI unit without commands: left out of the command line."""


class ShopProject(CliProject):
    cli_description = "The shop."
    greetings = Slot(Greetings)
    server = Slot(Server)
    fail = Slot(Fail)
    hidden = Slot(Hidden)
    empty = Slot(Empty)

    async def configure(self) -> None:
        PROJECTS.append(weakref.ref(self))
        EVENTS.append("configure")

    async def shut_down(self) -> None:
        EVENTS.append("shut down")


class NoCommandsProject(CliProject):
    empty = Slot(Empty)
    hidden = Slot(Hidden)


class PlainProject(Project):
    """Not a CLI project: adds no options, gets no arguments."""

    greetings = Slot(Greetings)
