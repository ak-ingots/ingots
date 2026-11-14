"""The unit: an entity grouping other entities."""

__all__ = ("Unit",)

import typing as t
import weakref

from .entity import Entity
from .slots import SlotsOwner


class Unit(SlotsOwner, Entity):
    """An entity grouping other entities in slots, their parent."""

    _unit_parents: "tuple[weakref.ref[SlotsOwner], ...]"

    @t.override
    def _slots_get_parents(self) -> "tuple[weakref.ref[SlotsOwner], ...]":
        try:
            return self._unit_parents
        except AttributeError:
            pass
        self._unit_parents = (*self._entity_parents, weakref.ref(self))
        return self._unit_parents

    @t.override
    def _slots_get_full_name(self) -> str:
        return self.full_name
