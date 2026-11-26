"""The command: what a runner runs."""

__all__ = ("BaseCommand",)

import abc
import typing as t

from ingots.puer.entity import Entity

from .node import CliNode


class BaseCommand(CliNode, Entity):
    """
    A leaf of the command line: the work a runner runs, its sub-command the
    name of its slot. A command either finishes by itself or runs until
    :meth:`stop` asks it to finish. It reaches the domain it serves through
    its project: ``self.project.settings``.

    :attr:`cli_is_quiet` on, its output is its own: the configs are not
    printed on configuring, ``IS_PRINT_CONFIGS`` off unless the command line
    turns it on; for a command printing for an operator or a shell.
    """

    cli_is_quiet: t.ClassVar[bool] = False

    @abc.abstractmethod
    async def _run(self) -> None:
        """Does the work. An exception fails the run with exit code 1."""
        raise NotImplementedError(f"{type(self).__qualname__}.run")

    def _stop(self) -> None:
        """
        Asks the running command to finish. Does nothing by default: the
        runner cancels a command that is still running after the graceful
        timeout.
        """
