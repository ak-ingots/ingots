"""The owner of slots: a project or a unit."""

__all__ = ("SlotsOwner",)

import abc
import contextlib
import inspect
import typing as t

from ingots.puer.entity import Entity

from .base import BaseSlot
from .entity import Slot

if t.TYPE_CHECKING:
    from collections.abc import Iterator

    from ingots.puer.project import Project


class SlotsOwner:
    """
    A class whose instances own the entities of their slots: a project or a
    unit. Its slots are checked and indexed when a subclass is created.

    The ``slots_`` methods walk them without creating anything, all of them
    or those holding one kind of entity (units, commands, ...),
    and find an entity by its dotted path:
    ``project.slots_find_entity("storage.repository", Repository)``.
    """

    # the slots of the class, own and inherited, in declaration order; set
    # on the class itself, see _get_index()
    _slots_index: t.ClassVar[dict[str, BaseSlot[t.Any]]] = {}

    @t.override
    @classmethod
    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        _get_index(cls)

    @t.overload
    @classmethod
    def slots_iter(cls) -> "Iterator[tuple[str, BaseSlot[t.Any]]]": ...

    @t.overload
    @classmethod
    def slots_iter[EntityType: Entity](
        cls, kind: type[EntityType]
    ) -> "Iterator[tuple[str, BaseSlot[EntityType]]]": ...

    @t.final
    @classmethod
    def slots_iter(
        cls, kind: type[Entity] = Entity
    ) -> "Iterator[tuple[str, BaseSlot[t.Any]]]":
        """
        The slots of the class holding ``kind``, own and inherited, in
        declaration order, with their names.
        """
        for name, slot in _get_index(cls).items():
            if issubclass(slot.cls, kind):
                yield name, slot

    @t.overload
    @classmethod
    def slots_walk(cls) -> "Iterator[tuple[str, BaseSlot[t.Any]]]": ...

    @t.overload
    @classmethod
    def slots_walk[EntityType: Entity](
        cls, kind: type[EntityType]
    ) -> "Iterator[tuple[str, BaseSlot[EntityType]]]": ...

    @t.final
    @classmethod
    def slots_walk(
        cls, kind: type[Entity] = Entity
    ) -> "Iterator[tuple[str, BaseSlot[t.Any]]]":
        """
        The slots holding ``kind`` under the class and, depth first, under the
        units in it, in declaration order, with their dotted paths
        (``storage.redis``).
        """
        for name, slot in _get_index(cls).items():
            if issubclass(slot.cls, kind):
                yield name, slot
            if issubclass(slot.cls, SlotsOwner):
                for path, child in slot.cls.slots_walk(kind):
                    yield f"{name}.{path}", child

    @t.overload
    def slots_find_entity(self, path: str) -> Entity: ...

    @t.overload
    def slots_find_entity[EntityType: Entity](
        self, path: str, kind: type[EntityType]
    ) -> EntityType: ...

    @t.final
    def slots_find_entity(self, path: str, kind: type[Entity] = Entity) -> Entity:
        """
        The entity at a dotted path under the owner, created with the units on
        the way if they are not yet.

        :raises LookupError: no slot holding ``kind`` is at the path, or a
            factory is, which holds no entity.
        """
        slot = dict(type(self).slots_walk(kind)).get(path)
        if not isinstance(slot, Slot):
            raise LookupError(f"no slot of {kind.__qualname__} at {path!r}")
        entity: object = self
        for name in path.split("."):
            entity = getattr(entity, name)
        return t.cast(Entity, entity)

    @t.overload
    def slots_walk_entities(self) -> "Iterator[Entity]": ...

    @t.overload
    def slots_walk_entities[EntityType: Entity](
        self, kind: type[EntityType]
    ) -> "Iterator[EntityType]": ...

    @t.final
    def slots_walk_entities(self, kind: type[Entity] = Entity) -> "Iterator[Entity]":
        """
        The entities of ``kind`` created so far under the owner and, depth
        first, under the units among them, in declaration order.
        """
        for slot in _get_index(type(self)).values():
            for entity in slot._iter_entities(self):
                if isinstance(entity, kind):
                    yield entity
                if isinstance(entity, SlotsOwner):
                    yield from entity.slots_walk_entities(kind)

    @t.final
    def slots_find_path(self, entity: Entity) -> str:
        """
        The dotted path of an entity created under the owner, as
        :meth:`slots_find_entity` takes it.

        :raises LookupError: the entity is not under the owner.
        """
        for name, slot in _get_index(type(self)).items():
            for child in slot._iter_entities(self):
                if child is entity:
                    return name
                if isinstance(child, SlotsOwner):
                    with contextlib.suppress(LookupError):
                        return f"{name}.{child.slots_find_path(entity)}"
        raise LookupError(f"no slot of {self!r} holds {entity!r}")

    @abc.abstractmethod
    def _slots_get_project(self) -> "Project":
        """The project the entities of this owner's slots belong to."""
        raise NotImplementedError(f"{type(self).__qualname__}._slots_get_project")


def check_slots(cls: type[SlotsOwner]) -> None:
    """
    Internal, run when the class is created: a slot of a subclass must hold
    a subclass of what every direct base holds in it. Where two bases hold
    unrelated classes in one slot, the subclass declares the slot with a
    class extending all of them.
    """
    for base in cls.__bases__:
        if not issubclass(base, SlotsOwner):
            continue
        for name, base_slot in _get_index(base).items():
            slot = inspect.getattr_static(cls, name)
            if isinstance(slot, BaseSlot) and slot._extends(base_slot):
                continue
            raise TypeError(
                f"{cls.__qualname__}.{name} = {slot!r} does not extend "
                f"{base.__qualname__}.{name} = {base_slot!r}: declare "
                f"{cls.__qualname__}.{name} with a class extending the classes "
                f"of all bases"
            )


def _get_index(cls: type[SlotsOwner]) -> dict[str, BaseSlot[t.Any]]:
    # built when the class is created; a subclass whose __init_subclass__
    # forgets super() gets it checked and built on its first walk instead
    index: dict[str, BaseSlot[t.Any]] | None = vars(cls).get("_slots_index")
    if index is None:
        check_slots(cls)
        index = {}
        for klass in reversed(cls.__mro__):
            for name, value in vars(klass).items():
                if isinstance(value, BaseSlot) and name not in index:
                    index[name] = inspect.getattr_static(cls, name)
        cls._slots_index = index
    return index
