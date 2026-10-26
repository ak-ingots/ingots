"""The base of the slots: the declaration of a child of a project or a unit."""

__all__ = ("BaseSlot",)

import typing as t

if t.TYPE_CHECKING:
    from collections.abc import Iterator

    from ingots.puer.entity import Entity

    from .owner import SlotsOwner


class BaseSlot[EntityType: Entity]:
    """
    A child of a project or a unit, declared on its class: the class it
    creates and the rules of its replacement in a subclass. A kind of slot
    gives what it holds on the instance with ``__get__``: :class:`Slot` an
    entity, :class:`Factory` a function creating them.

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

    @t.final
    def __set__(self, obj: "SlotsOwner", value: t.Never) -> t.NoReturn:
        raise AttributeError(f"{self._name} is a slot: declare it again in a subclass")

    @t.override
    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self._cls.__qualname__})"

    def _extends(self, base: "BaseSlot[t.Any]") -> bool:
        """
        Whether this slot may replace ``base`` in a subclass: it is of the
        same kind and holds a subclass of the base's class.
        """
        return isinstance(self, type(base)) and issubclass(self._cls, base.cls)

    def _iter_entities(self, owner: "SlotsOwner") -> "Iterator[EntityType]":
        """The entities of ``owner`` the slot holds: none here."""
        yield from ()
