"""The command: what a runner runs."""

__all__ = ("BaseCommand",)

import abc

from ingots.puer.entity import Entity

from .node import CliNode


class BaseCommand(CliNode, Entity):
    """
    A leaf of the command line: the work a runner runs. A command either
    finishes by itself or runs until :meth:`stop` asks it to finish.
    """

    @abc.abstractmethod
    async def run(self) -> None:
        """Does the work. An exception fails the run with exit code 1."""
        raise NotImplementedError(f"{type(self).__qualname__}.run")

    def stop(self) -> None:
        """
        Asks the running command to finish. Does nothing by default: the
        runner cancels a command that is still running after the graceful
        timeout.
        """
