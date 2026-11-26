"""The project tested by its own command."""

__all__ = ("TestingCliUnit", "TestingCommandsUnit", "TestingProject")

from ingots.defaults import Project
from ingots.defaults.cli import CliUnit, CommandsUnit
from ingots.puer import Slot

from .commands import RunTestsCommand


class TestingCommandsUnit(CommandsUnit):
    """The tests of the project on the command line: ``testing run``."""

    cli_description = "The tests of the project."
    run = Slot(RunTestsCommand)


class TestingCliUnit(CliUnit):
    """The command line of the defaults and ``testing``."""

    testing = Slot(TestingCommandsUnit)


class TestingProject(Project):
    """
    A project whose tests run by its own command, ``python -m app testing
    run``, configured as the project is: the scenarios of an application,
    a client of it. Its fixtures outside the command raise
    :class:`~ingots.testing.OutsideRunError`. A project of an addon with
    commands of its own joins its unit ``cli`` with :class:`TestingCliUnit`.
    """

    cli = Slot(TestingCliUnit)
