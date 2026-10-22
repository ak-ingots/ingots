"""The slot of an entity: one child of its owner, created on first access."""

__all__ = ("Slot",)

import typing as t

if t.TYPE_CHECKING:
    from collections.abc import Iterator

    from ingots.puer.entity import Entity

    from .owner import SlotsOwner


class Slot[EntityType: Entity]:
    """
    One entity per owner, created on first access and owned by it. On the
    class it is the slot itself. A subclass customizes it by declaring the
    slot again with a subclass of the entity class:
    ``unit = Slot(MyUnit)`` where ``MyUnit`` extends the base's class.

    A kind of slot extends it through the hooks: :meth:`_iter_entities`,
    :meth:`_extends`.
    """

    def __init__(self, cls: type[EntityType]) -> None:
        self._cls = cls

    @t.final
    @property
    def cls(self) -> type[EntityType]:
        """The entity class this slot creates."""
        return self._cls

    def __set_name__(self, owner: type, name: str) -> None:
        from .owner import SlotsOwner  # the owner module imports this one

        if not issubclass(owner, SlotsOwner):
            raise TypeError(
                f"{owner.__qualname__}.{name}: slots belong to projects and units"
            )
        self._name, self._key = name, f"_slot_{name}"

    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...

    @t.overload
    def __get__(self, obj: "SlotsOwner", owner: type) -> EntityType: ...

    @t.final
    def __get__(self, obj: "SlotsOwner | None", owner: type) -> t.Self | EntityType:
        if obj is None:
            return self

        entity: EntityType | None = obj.__dict__.get(self._key)
        if entity is None:
            entity = obj.__dict__[self._key] = self._cls(obj._slots_get_project())
        return entity

    @t.final
    def __set__(self, obj: "SlotsOwner", value: t.Never) -> t.NoReturn:
        raise AttributeError(f"{self._name} is a slot: declare it again in a subclass")

    @t.override
    def __repr__(self) -> str:
        return f"Slot({self._cls.__qualname__})"

    def _extends(self, base: "Slot[t.Any]") -> bool:
        """
        Whether this slot may replace ``base`` in a subclass: it is of the
        same kind and holds a subclass of the base's class.
        """
        return isinstance(self, type(base)) and issubclass(self._cls, base.cls)

    def _iter_entities(self, owner: "SlotsOwner") -> "Iterator[EntityType]":
        """The entities of ``owner`` created so far: one at most here."""
        entity: EntityType | None = owner.__dict__.get(self._key)
        if entity is not None:
            yield entity
