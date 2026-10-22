"""The commands of the components."""

__all__ = ("ListComponentsCommand", "RunComponentsForeverCommand", "RunForeverCliArgs")

import argparse
import asyncio
import logging
import typing as t
from dataclasses import dataclass

from ingots.puer import Component
from ingots.puer.cli import BaseCommand

if t.TYPE_CHECKING:
    from ingots.defaults.project import Project

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RunForeverCliArgs:
    components: tuple[str, ...]


class ListComponentsCommand(BaseCommand):
    """Prints the components of the project, as ``run-forever`` takes them."""

    cli_description = "Prints the components of the project."
    project: "Project"

    @t.override
    async def _run(self) -> None:
        self.project.components.print_components()


class RunComponentsForeverCommand(BaseCommand):
    """
    Configures the given components, servers typically, and keeps them
    running until stopped; the project shuts them down.
    """

    cli_description = "Runs the given components until stopped."
    cli_args: RunForeverCliArgs

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--component",
            dest="run_forever_components",
            action="append",
            required=True,
            metavar="PATH",
            help="a component to run, as `components list` prints it; repeat "
            "for more",
        )

    @t.override
    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> RunForeverCliArgs:
        return RunForeverCliArgs(tuple(namespace.run_forever_components))

    def __init__(self, project: "Project") -> None:
        super().__init__(project)
        self._stopped = asyncio.Event()

    @t.override
    async def _run(self) -> None:
        paths = self.cli_args.components
        components = [self.project.slots_find_entity(path, Component) for path in paths]
        await asyncio.gather(*components)
        logger.info("running %s until stopped", ", ".join(paths))
        await self._stopped.wait()

    @t.override
    def _stop(self) -> None:
        self._stopped.set()
