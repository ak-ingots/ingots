"""The project tested by its own command."""

__all__ = ("TestingProject", "TestingUnit")

from ingots.defaults import Project
from ingots.puer import Slot
from ingots.puer.cli import CliUnit

from .commands import RunTestsCommand


class TestingUnit(CliUnit):
    """The tests of the project on the command line: ``testing run``."""

    cli_description = "The tests of the project."
    run = Slot(RunTestsCommand)


class TestingProject(Project):
    """
    A project whose tests run by its own command, ``python -m app testing
    run``, configured as the project is: the scenarios of an application,
    a client of it. Its fixtures outside the command raise
    :class:`~ingots.testing.OutsideRunError`.
    """

    testing = Slot(TestingUnit)
