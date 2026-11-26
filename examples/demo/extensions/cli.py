"""
The command line of the demo: that of the defaults, and ``demo greet``,
whose option ``--tone`` a shell completes by its choices.
"""

import argparse
import typing as t
from dataclasses import dataclass

from ingots.defaults.cli import BaseCommand, CliUnit, CommandsUnit
from ingots.puer import Slot

if t.TYPE_CHECKING:
    from project import DemoProject


@dataclass(frozen=True, slots=True, kw_only=True)
class GreetCliArgs:
    name: str
    tone: str


class GreetCommand(BaseCommand):
    cli_description = "Greets someone."
    cli_args: GreetCliArgs
    project: "DemoProject"

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--name", dest="greet_name", default="world")
        parser.add_argument(
            "--tone", dest="greet_tone", choices=("casual", "formal"), default="casual"
        )

    @t.override
    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> GreetCliArgs:
        return GreetCliArgs(name=namespace.greet_name, tone=namespace.greet_tone)

    @t.override
    async def _run(self) -> None:
        print(self.project.greetings.greet(self.cli_args.name, self.cli_args.tone))


class DemoCommandsUnit(CommandsUnit):
    cli_description = "The commands of the demo."
    greet = Slot(GreetCommand)


class DemoCliUnit(CliUnit):
    demo = Slot(DemoCommandsUnit)
