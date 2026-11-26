"""The group of commands on the command line."""

__all__ = ("CommandsUnit",)

import typing as t

from ingots.puer.unit import Unit

from .command import BaseCommand
from .node import CliNode


class CommandsUnit(CliNode, Unit):
    """
    A sub-command, the name of its slot, grouping the commands and the groups
    of its slots: ``tags = Slot(AuthTagsCommandsUnit)``, ``list =
    Slot(AuthListTagsCommand)``. It holds nothing else: the domain its
    commands serve is reached through the project.

    :raises TypeError: at the creation of the class, a slot holds neither a
        command nor a group of commands.
    """

    @t.override
    @classmethod
    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        for name, slot in cls.slots_iter():
            if not issubclass(slot.cls, (CommandsUnit, BaseCommand)):
                raise TypeError(
                    f"{cls.__qualname__}.{name}: {slot.cls.__qualname__} is not "
                    "on the command line; a command reaches its domain through "
                    "the project"
                )
