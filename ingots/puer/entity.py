"""The entity: what a project is made of."""

__all__ = ("Entity",)

import typing as t
import weakref

if t.TYPE_CHECKING:
    from .project import Project


class Entity:
    """
    Belongs to exactly one project and holds only a weak reference to it. A
    subclass narrows the project's type with an annotation:
    ``project: "AppProject"``.
    """

    def __init__(self, project: "Project") -> None:
        self._project_ref = weakref.ref(project)

    @property
    def project(self) -> "Project":
        """
        The project, for immediate use. Do not keep it in an attribute or a
        callback: that keeps the project alive after its holder drops it.

        :raises ReferenceError: the project is gone.
        """
        project = self._project_ref()
        if project is None:
            raise ReferenceError(f"{type(self).__qualname__}: the project is gone")
        return project
