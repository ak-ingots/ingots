"""The project: the root of the tree."""

__all__ = ("Project",)

from .slots import SlotsOwner


class Project(SlotsOwner):
    """Owns every unit and entity created through its slots."""

    async def configure(self) -> None:
        """
        Prepares the project before a runner runs its workflow. Does nothing
        by default.
        """

    async def shut_down(self) -> None:
        """
        Releases what the project holds once the runner is done, whatever the
        workflow's outcome. Does nothing by default.
        """

    def _slots_get_project(self) -> "Project":
        return self
