"""
The command line of PUER: a project's CLI is built from its slots.

A :class:`CliUnit` is a sub-command grouping the commands of its slots, a
:class:`BaseCommand` is what a runner runs, and :class:`CommandRunner` runs
the command chosen on the command line, creating only what lies on its path.
"""

__all__ = (
    "BaseCommand",
    "CliParser",
    "CliProject",
    "CliTree",
    "CliUnit",
    "CommandRunner",
    "CommandRunnerCliArgs",
    "ParsedCommandLine",
)

from .command import BaseCommand
from .parser import CliParser, CliTree, ParsedCommandLine
from .project import CliProject
from .runner import CommandRunner, CommandRunnerCliArgs
from .unit import CliUnit
