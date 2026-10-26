"""The slot of a factory: a new entity on every call, owned by the caller."""

__all__ = ("BoundFactory", "Factory")

import typing as t

from ingots.puer.components import Component

from .base import BaseSlot
from .owner import SlotsOwner

if t.TYPE_CHECKING:
    from ingots.puer.entity import Entity


class Factory[EntityType: Entity](BaseSlot[EntityType]):
    """
    A new entity on every call, for one use at a time: an operation run
    concurrently, a handler of one request. On the instance the slot is a
    :class:`BoundFactory` creating one on the owner's project, on the class
    the slot itself; a subclass customizes it as a :class:`Slot`:
    ``pay = Factory(LoggedPay)`` where ``LoggedPay`` extends ``Pay``. Usage::

        class Shop(Unit):
            pay = Factory(Pay)

        pay = project.shop.pay()  # a new Pay

    The caller owns what it creates: the owner keeps nothing, so the
    project neither walks nor shuts it down. A component, which the
    project shuts down, or a unit, whose slots it walks, has a
    :class:`Slot` instead.

    :raises TypeError: the class is a component or a unit.
    """

    def __init__(self, cls: type[EntityType]) -> None:
        if issubclass(cls, (Component, SlotsOwner)):
            raise TypeError(
                f"Factory({cls.__qualname__}): a component or a unit has a Slot"
            )
        super().__init__(cls)

    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...

    @t.overload
    def __get__(self, obj: "SlotsOwner", owner: type) -> "BoundFactory[EntityType]": ...

    @t.final
    def __get__(
        self, obj: "SlotsOwner | None", owner: type
    ) -> "t.Self | BoundFactory[EntityType]":
        if obj is None:
            return self
        return BoundFactory(self._cls, obj)


@t.final
class BoundFactory[EntityType: Entity]:
    """
    A :class:`Factory` on its owner: calling it creates a new entity on the
    owner's project, and :attr:`cls` tells which before creating one, for
    the class attributes of an operation to check its caller first.
    """

    __slots__ = ("_cls", "_owner")

    def __init__(self, cls: type[EntityType], owner: SlotsOwner) -> None:
        self._cls = cls
        self._owner = owner

    @property
    def cls(self) -> type[EntityType]:
        """The class of the entities it creates."""
        return self._cls

    def __call__(self) -> EntityType:
        return self._cls(self._owner._slots_get_project())

    @t.override
    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self._cls.__qualname__})"
