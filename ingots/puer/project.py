"""The project: the root of the tree."""

__all__ = ("Project",)

from .slots import SlotsOwner


class Project(SlotsOwner):
    """Owns every unit and entity created through its slots."""

    def _slots_get_project(self) -> "Project":
        return self
