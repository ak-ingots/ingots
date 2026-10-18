"""The unit on the command line."""

__all__ = ("CliUnit",)

from ingots.puer.unit import Unit

from .node import CliNode


class CliUnit(CliNode, Unit):
    """
    A unit on the command line: a sub-command grouping the commands of its
    slots. A plain :class:`~ingots.puer.unit.Unit` and everything in it stay
    off the command line.
    """
