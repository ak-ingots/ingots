"""
The bases of the slots: the declaration of a child of a project or a unit,
of one class or of several.
"""

__all__ = ("BaseClassesSlot", "BaseClassSlot", "BaseSlot")

import typing as t

from ingots.puer.entity import create_entity

if t.TYPE_CHECKING:
    from collections.abc import Iterator

    from ingots.puer.entity import Entity

    from .owner import SlotsOwner


class BaseSlot[EntityType: Entity]:
    """
    Children of a project or a unit, declared on its class: the rules of its
    replacement in a subclass. A kind of slot gives what it holds on the
    instance with ``__get__``, each entity created by :meth:`create_entity`.
    It holds one class, :class:`BaseClassSlot`, or several,
    :class:`BaseClassesSlot`.

    A kind of slot extends it through the hooks: :meth:`_prepare_entity`,
    :meth:`_iter_entities`, :meth:`_extends`.
    """

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

    @t.final
    def create_entity(self, cls: type[EntityType], parent: "SlotsOwner") -> EntityType:
        """
        An entity of the slot under a parent, its owner: its place first, the
        parents of the parent and the name of the slot, then what the kind of
        slot gives it, :meth:`_prepare_entity`, then its ``__init__``, which
        has them all.

        :raises ReferenceError: the project is gone.
        """
        return create_entity(
            cls,
            parent,
            self._name,
            before_init=lambda entity: self._prepare_entity(entity, parent),
        )

    def _prepare_entity(self, entity: EntityType, parent: "SlotsOwner") -> None:
        """
        What the kind of slot gives its entities before their ``__init__``,
        their place set: nothing here.
        """

    def _extends(self, base: "BaseSlot[t.Any]") -> bool:
        """Whether this slot may replace ``base`` in a subclass: of the same kind."""
        return isinstance(self, type(base))

    def _iter_entities(self, owner: "SlotsOwner") -> "Iterator[EntityType]":
        """The entities of ``owner`` the slot holds: none here."""
        yield from ()


class BaseClassSlot[EntityType: Entity](BaseSlot[EntityType]):
    """
    A slot of one class: :class:`Slot` an entity, :class:`Factory` a
    function creating them. A subclass replaces it with a slot of the same
    kind holding a subclass of its class.
    """

    def __init__(self, cls: type[EntityType]) -> None:
        self._cls = cls

    @t.final
    @property
    def cls(self) -> type[EntityType]:
        """The entity class this slot creates."""
        return self._cls

    @t.override
    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self._cls.__qualname__})"

    @t.override
    def _extends(self, base: "BaseSlot[t.Any]") -> bool:
        """
        Whether this slot may replace ``base`` in a subclass: it is of the
        same kind and holds a subclass of the base's class.
        """
        return super()._extends(base) and issubclass(
            self._cls, t.cast(BaseClassSlot[t.Any], base).cls
        )


class BaseClassesSlot[EntityType: Entity](BaseSlot[EntityType]):
    """
    A slot of several classes, in their order, a class once:
    :class:`Factories` functions creating an entity of each. A subclass
    replaces it with a slot of the same kind holding any classes, those of
    its base taken from :attr:`classes`, some added, dropped or replaced::

        checks = Factories[BaseOperation[Order, t.Any]](
            *ShopUnit.checks.classes, AppStockOperation
        )

    The type of its entities is given, never inferred: inferred from
    classes of different bases, it is ``Never``, and the error comes where
    the slot is used. Given, mypy checks each class against it, and the
    slot of a subclass against that of its base.
    """

    def __init__(self, *classes: type[EntityType]) -> None:
        self._classes = tuple(dict.fromkeys(classes))

    @t.final
    @property
    def classes(self) -> tuple[type[EntityType], ...]:
        """The entity classes this slot creates, in their order."""
        return self._classes

    @t.override
    def __repr__(self) -> str:
        names = ", ".join(cls.__qualname__ for cls in self._classes)
        return f"{type(self).__qualname__}({names})"
