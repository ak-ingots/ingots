"""The unit: an entity grouping other entities."""

__all__ = ("Unit",)

import typing as t

from .entity import Entity
from .slots import SlotsOwner

if t.TYPE_CHECKING:
    from .project import Project


class Unit(SlotsOwner, Entity):
    """An entity grouping other entities in slots."""

    @t.override
    def _slots_get_project(self) -> "Project":
        return self.project
