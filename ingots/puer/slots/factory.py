"""
The slots of factories: a new entity on every call, owned by the caller, of
one class or of each of several.
"""

__all__ = ("BoundFactories", "BoundFactory", "Factories", "Factory")

import typing as t

from ingots.puer.components import Component

from .base import BaseClassesSlot, BaseClassSlot
from .owner import SlotsOwner

if t.TYPE_CHECKING:
    from ingots.puer.entity import Entity


class Factory[EntityType: Entity](BaseClassSlot[EntityType]):
    """
    A new entity on every call, for one use at a time: an operation run
    concurrently, a handler of one request. On the instance the slot is a
    :class:`BoundFactory` creating one on the owner's project, on the class
    the slot itself; a subclass customizes it as a :class:`Slot`:
    ``pay = Factory(LoggedPayOperation)`` where ``LoggedPayOperation``
    extends ``PayOperation``. Usage::

        class ShopUnit(Unit):
            pay = Factory(PayOperation)

        pay = project.shop.pay()  # a new PayOperation

    The caller owns what it creates: the owner keeps nothing, so the
    project neither walks nor shuts it down. A component, which the
    project shuts down, or a unit, whose slots it walks, has a
    :class:`Slot` instead.

    :raises TypeError: the class is a component or a unit.
    """

    def __init__(self, cls: type[EntityType]) -> None:
        _check_class(type(self), cls)
        super().__init__(cls)

    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...

    @t.overload
    def __get__(self, obj: "SlotsOwner", owner: type) -> "BoundFactory[EntityType]": ...

    @t.final
    def __get__(
        self, obj: "SlotsOwner | None", owner: type
    ) -> "t.Self | BoundFactory[EntityType]":
        if obj is None:
            return self
        return BoundFactory(self._cls, obj)


@t.final
class BoundFactory[EntityType: Entity]:
    """
    A :class:`Factory` on its owner: calling it creates a new entity on the
    owner's project, and :attr:`cls` tells which before creating one, for
    the class attributes of an operation to check its caller first.
    """

    __slots__ = ("_cls", "_owner")

    def __init__(self, cls: type[EntityType], owner: SlotsOwner) -> None:
        self._cls = cls
        self._owner = owner

    @property
    def cls(self) -> type[EntityType]:
        """The class of the entities it creates."""
        return self._cls

    def __call__(self) -> EntityType:
        return self._cls(self._owner._slots_get_project())

    @t.override
    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self._cls.__qualname__})"


class Factories[EntityType: Entity](BaseClassesSlot[EntityType]):
    """
    A new entity of each of its classes on every call, in their order: the
    operations a runner runs together, ``run_group()`` of the operations of
    the defaults. On the instance the slot is a :class:`BoundFactories`,
    on the class the slot itself; a subclass declares it again, from the
    classes of its base. Usage::

        class ShopUnit(Unit):
            checks = Factories[BaseOperation[Order, t.Any]](
                StockOperation, LimitOperation
            )

        class AppShopUnit(ShopUnit):
            checks = Factories[BaseOperation[Order, t.Any]](
                *ShopUnit.checks.classes, FraudOperation
            )

        checks = project.shop.checks()  # a new entity of each class

    The caller owns what it creates, as of a :class:`Factory`.

    :raises TypeError: a class is a component or a unit.
    """

    def __init__(self, *classes: type[EntityType]) -> None:
        for cls in classes:
            _check_class(type(self), cls)
        super().__init__(*classes)

    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...

    @t.overload
    def __get__(
        self, obj: "SlotsOwner", owner: type
    ) -> "BoundFactories[EntityType]": ...

    @t.final
    def __get__(
        self, obj: "SlotsOwner | None", owner: type
    ) -> "t.Self | BoundFactories[EntityType]":
        if obj is None:
            return self
        return BoundFactories(self._classes, obj)


@t.final
class BoundFactories[EntityType: Entity]:
    """
    A :class:`Factories` on its owner: calling it creates a new entity of
    each class on the owner's project, and :attr:`classes` tells which
    before creating any.
    """

    __slots__ = ("_classes", "_owner")

    def __init__(
        self, classes: tuple[type[EntityType], ...], owner: SlotsOwner
    ) -> None:
        self._classes = classes
        self._owner = owner

    @property
    def classes(self) -> tuple[type[EntityType], ...]:
        """The classes of the entities it creates, in their order."""
        return self._classes

    def __call__(self) -> tuple[EntityType, ...]:
        project = self._owner._slots_get_project()
        return tuple(cls(project) for cls in self._classes)

    @t.override
    def __repr__(self) -> str:
        names = ", ".join(cls.__qualname__ for cls in self._classes)
        return f"{type(self).__qualname__}({names})"


def _check_class(slot: type, cls: type) -> None:
    # a component is shut down by its project, a unit walked: both are owned
    if issubclass(cls, (Component, SlotsOwner)):
        raise TypeError(
            f"{slot.__qualname__}({cls.__qualname__}): a component or a unit "
            f"has a Slot"
        )
