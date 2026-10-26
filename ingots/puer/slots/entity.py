"""The slot of an entity: one child of its owner, created on first access."""

__all__ = ("Slot",)

import typing as t

from .base import BaseSlot

if t.TYPE_CHECKING:
    from collections.abc import Iterator

    from ingots.puer.entity import Entity

    from .owner import SlotsOwner


class Slot[EntityType: Entity](BaseSlot[EntityType]):
    """
    One entity per owner, created on first access and owned by it. On the
    class it is the slot itself. A subclass customizes it by declaring the
    slot again with a subclass of the entity class:
    ``unit = Slot(MyUnit)`` where ``MyUnit`` extends the base's class.
    """

    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...

    @t.overload
    def __get__(self, obj: "SlotsOwner", owner: type) -> EntityType: ...

    @t.final
    def __get__(self, obj: "SlotsOwner | None", owner: type) -> t.Self | EntityType:
        if obj is None:
            return self

        try:
            entity: EntityType = obj.__dict__[self._key]
        except KeyError:
            entity = obj.__dict__[self._key] = self._cls(obj._slots_get_project())
        return entity

    @t.override
    def _iter_entities(self, owner: "SlotsOwner") -> "Iterator[EntityType]":
        """The entities of ``owner`` created so far: one at most here."""
        entity: EntityType | None = owner.__dict__.get(self._key)
        if entity is not None:
            yield entity
