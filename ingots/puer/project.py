"""The project: the root of the tree."""

__all__ = ("Project",)

import typing as t

from .constants import ProjectState
from .slots import SlotsOwner


class Project(SlotsOwner):
    """
    Owns every unit and entity created through its slots. The runner shuts
    it down: :meth:`_shut_down` releases what it holds.
    """

    _project_state = ProjectState.ACTIVE

    @t.final
    @property
    def state(self) -> ProjectState:
        """Where the project is in its life."""
        return self._project_state

    @t.final
    async def _do_shut_down(self) -> None:
        """
        Releases what the project holds once the runner is done, whatever the
        workflow's outcome: what :meth:`_shut_down` releases. Shutting down
        twice does nothing. Internal: the runner calls it.
        """
        if self._project_state is not ProjectState.ACTIVE:
            return

        self._project_state = ProjectState.SHUTTING_DOWN
        try:
            await self._shut_down()
        finally:
            self._project_state = ProjectState.SHUT_DOWN

    async def _configure(self) -> None:
        """
        Prepares the project before the runner runs its workflow. Does nothing
        here: an override needs ``super()`` only to keep what its bases do.
        """

    async def _shut_down(self) -> None:
        """
        Releases what the project holds. Does nothing here: an override needs
        ``super()`` only to keep what its bases release.
        """

    @t.override
    def _slots_get_project(self) -> "Project":
        return self
