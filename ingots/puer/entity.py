"""The entity: what a project is made of."""

__all__ = ("Entity", "create_entity")

import functools
import typing as t
import weakref

if t.TYPE_CHECKING:
    from collections.abc import Callable

    from .project import Project
    from .slots import SlotsOwner

Parents: t.TypeAlias = "tuple[weakref.ref[SlotsOwner], ...]"


class Entity:
    """
    Belongs to exactly one project, under its parents, at its name: its
    owner, the slot or the factory of its attribute, sets them before its
    ``__init__``, which takes none, so that ``__init__`` has them already.
    The rest follows: :attr:`project`, the first of the parents,
    :attr:`parent`, the last, :attr:`full_name`, the dotted path from the
    project, :meth:`find_parent`, the nearest of a kind. The parents are weak
    references. A subclass narrows the types with annotations:
    ``project: "AppProject"``, ``parent: "ShopUnit"``.
    """

    _entity_parents: Parents
    _entity_name: str

    def __init__(self) -> None:
        """Takes nothing: the place is set before, by the owner."""

    @property
    def project(self) -> "Project":
        """
        The project, for immediate use. Do not keep it in an attribute or a
        callback: that keeps the project alive after its holder drops it.

        :raises ReferenceError: the project is gone.
        """
        return t.cast("Project", self._entity_get_parent(0))

    @property
    def parent(self) -> "SlotsOwner":
        """
        The owner of the slot the entity was created by: a unit, or the
        project. For immediate use, as :attr:`project`.

        :raises ReferenceError: the parent is gone.
        """
        return self._entity_get_parent(-1)

    @t.final
    @property
    def parents(self) -> "tuple[SlotsOwner, ...]":
        """
        The parents, from the project to the parent, for immediate use.

        :raises ReferenceError: one is gone.
        """
        return tuple(
            self._entity_get_parent(index) for index in range(len(self._entity_parents))
        )

    @t.final
    @property
    def name(self) -> str:
        """The name of the attribute of the parent holding it."""
        return self._entity_name

    @t.final
    @functools.cached_property
    def full_name(self) -> str:
        """The dotted path from the project, ``shop.stock``, built once."""
        prefix = self.parent._slots_get_full_name()
        return f"{prefix}.{self._entity_name}" if prefix else self._entity_name

    @t.final
    def find_parent[ParentType](self, kind: type[ParentType]) -> ParentType:
        """
        The nearest of the parents of a kind.

        :raises LookupError: none is.
        :raises ReferenceError: a parent is gone.
        """
        for parent in reversed(self.parents):
            if isinstance(parent, kind):
                return parent
        raise LookupError(f"{self.full_name}: no parent of {kind.__qualname__}")

    @t.final
    def _entity_set_place(self, parents: Parents, name: str) -> None:
        """
        Internal, the one call of the owner before ``__init__``: the parents,
        from the project to the parent, and the name of the attribute.
        """
        self._entity_parents = parents
        self._entity_name = name

    @t.final
    def _entity_get_parent(self, index: int) -> "SlotsOwner":
        parent = self._entity_parents[index]()
        if parent is None:
            raise ReferenceError(f"{type(self).__qualname__}: the project is gone")
        return parent


def create_entity[EntityType: Entity](
    cls: type[EntityType],
    parent: "SlotsOwner",
    name: str | None = None,
    *,
    before_init: "Callable[[EntityType], None] | None" = None,
) -> EntityType:
    """
    An entity under a parent: its place, the parents of the parent and the
    name, that of its class by default, then what ``before_init`` gives it,
    then its ``__init__``, which has them all. The slots create theirs so,
    by :meth:`~ingots.puer.slots.BaseSlot.create_entity`, their name theirs
    and their hook ``before_init``; an entity out of the slots, a component
    made once, an entity of a test, is created by hand so.

    :raises ReferenceError: the project is gone: an entity of no project is
        not created.
    """
    parents = parent._slots_get_parents()
    if parents[0]() is None:
        raise ReferenceError(f"{cls.__qualname__}: the project is gone")
    entity = cls.__new__(cls)
    entity._entity_set_place(parents, name or cls.__qualname__)
    if before_init is not None:
        before_init(entity)
    entity.__init__()  # type: ignore[misc]
    return entity
