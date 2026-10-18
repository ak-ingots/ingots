"""Slots: a parent declares its children as typed descriptors."""

__all__ = ("Slot", "SlotsOwner", "check_slots", "iter_slots")

import abc
import inspect
import typing as t

if t.TYPE_CHECKING:
    from .entity import Entity
    from .project import Project


class SlotsOwner:
    """
    A class whose instances own the entities of their slots: a project or a
    unit. Its slots are checked when a subclass is created.
    """

    @classmethod
    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        check_slots(cls)

    @abc.abstractmethod
    def _slots_get_project(self) -> "Project":
        """The project the entities of this owner's slots belong to."""
        raise NotImplementedError(f"{type(self).__qualname__}._slots_get_project")


class Slot[EntityType: Entity]:
    """
    One entity per owner, created on first access and owned by it. On the
    class it is the slot itself. A subclass customizes it by declaring the
    slot again with a subclass of the entity class:
    ``unit = Slot(MyUnit)`` where ``MyUnit`` extends the base's class.
    """

    def __init__(self, cls: type[EntityType]) -> None:
        self._cls = cls

    @property
    def cls(self) -> type[EntityType]:
        """The entity class this slot creates."""
        return self._cls

    def __set_name__(self, owner: type, name: str) -> None:
        if not issubclass(owner, SlotsOwner):
            raise TypeError(
                f"{owner.__qualname__}.{name}: slots belong to projects and units"
            )
        self._name, self._key = name, f"_slot_{name}"

    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...

    @t.overload
    def __get__(self, obj: SlotsOwner, owner: type) -> EntityType: ...

    def __get__(self, obj: SlotsOwner | None, owner: type) -> t.Self | EntityType:
        if obj is None:
            return self

        entity: EntityType | None = obj.__dict__.get(self._key)
        if entity is None:
            entity = obj.__dict__[self._key] = self._cls(obj._slots_get_project())
        return entity

    def __set__(self, obj: SlotsOwner, value: t.Never) -> t.NoReturn:
        raise AttributeError(f"{self._name} is a slot: declare it again in a subclass")

    def __repr__(self) -> str:
        return f"Slot({self._cls.__qualname__})"


def check_slots(cls: type) -> None:
    """
    A slot of a subclass must hold a subclass of what every direct base holds
    in it. Where two bases hold unrelated classes in one slot, the subclass
    declares the slot with a class extending all of them.
    """
    for base in cls.__bases__:
        for name, base_slot in iter_slots(base):
            slot = inspect.getattr_static(cls, name)
            if isinstance(slot, Slot) and issubclass(slot.cls, base_slot.cls):
                continue
            raise TypeError(
                f"{cls.__qualname__}.{name} = {slot!r} does not extend "
                f"{base.__qualname__}.{name} = {base_slot!r}: declare "
                f"{cls.__qualname__}.{name} with a class extending the classes "
                f"of all bases"
            )


def iter_slots(cls: type) -> t.Iterator[tuple[str, Slot[t.Any]]]:
    """The slots of a class, own and inherited, in declaration order."""
    seen: set[str] = set()
    for klass in reversed(cls.__mro__):
        for name, value in vars(klass).items():
            if isinstance(value, Slot) and name not in seen:
                seen.add(name)
                yield name, inspect.getattr_static(cls, name)
