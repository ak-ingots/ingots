"""
A domain of the events: a shop whose payments are told to their subscribers,
a receipt, an audit of the staff, one that fails, one that tells of the
shipping in turn; with a transaction of its own, holding the events of its
block and dropping them on its rollback, as the facade of an addon does.
"""

import asyncio
import contextlib
import typing as t
from collections.abc import AsyncIterator
from dataclasses import dataclass

from ingots.defaults import Project
from ingots.defaults.operations import (
    BaseOperation,
    OperationMetadata,
    OperationsOwner,
    PermissionFlags,
    Permissions,
    PermissionsSlot,
)
from ingots.puer import Factories, Slot, Unit


@dataclass(frozen=True, slots=True, kw_only=True)
class Paid:
    amount: int


@dataclass(frozen=True, slots=True, kw_only=True)
class Shipped:
    amount: int


class Subscriber[EventType](BaseOperation[EventType, None]):
    """A subscriber anyone's event reaches, telling the shop what it saw."""

    project: "EventsProject"

    @t.override
    def _get_permissions(self) -> Permissions:
        return Permissions()


class ReceiptOperation(Subscriber[Paid]):
    @t.override
    async def _run(self, parameters: Paid, metadata: OperationMetadata) -> None:
        self.project.shop.seen.append(f"receipt {parameters.amount}")


class AuditOperation(Subscriber[Paid]):
    """Of the staff alone."""

    parent: "ShopUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.AUDIT)

    @t.override
    async def _run(self, parameters: Paid, metadata: OperationMetadata) -> None:
        self.project.shop.seen.append(f"audit {parameters.amount}")


class BrokenOperation(Subscriber[Paid]):
    @t.override
    async def _run(self, parameters: Paid, metadata: OperationMetadata) -> None:
        raise ConnectionError("the analytics are down")


class ShipOperation(Subscriber[Paid]):
    """Tells of the shipping in turn, after a while."""

    @t.override
    async def _run(self, parameters: Paid, metadata: OperationMetadata) -> None:
        await asyncio.sleep(0.01)
        shop = self.project.shop
        self.project.events.publish(
            shop.ev_shipped, Shipped(amount=parameters.amount), metadata
        )


class LabelOperation(Subscriber[Shipped]):
    @t.override
    async def _run(self, parameters: Shipped, metadata: OperationMetadata) -> None:
        self.project.shop.seen.append(f"label {parameters.amount}")


class ShopUnit(OperationsOwner, Unit):
    class Flags(PermissionFlags):
        AUDIT = 1 << 0

    project: "EventsProject"

    permissions = PermissionsSlot(Flags)

    ev_paid = Factories[BaseOperation[Paid, None]](ReceiptOperation)
    ev_shipped = Factories[BaseOperation[Shipped, None]](LabelOperation)

    def __init__(self) -> None:
        super().__init__()
        self.seen: list[str] = []
        self.is_in_transaction = False

    @contextlib.asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """
        Holds the events of its block: sent once committed, dropped on a
        rollback; inside another, it is that one.
        """
        if self.is_in_transaction:
            yield
            return
        async with self.project.events.hold() as held:
            self.is_in_transaction = True
            try:
                yield
            except BaseException:
                held.discard()
                raise
            finally:
                self.is_in_transaction = False


class FullShopUnit(ShopUnit):
    """Every subscriber: the receipt, the audit, the broken, the shipping."""

    ev_paid = Factories[BaseOperation[Paid, None]](
        *ShopUnit.ev_paid.classes, AuditOperation, BrokenOperation, ShipOperation
    )


class EventsProject(Project):
    shop = Slot(ShopUnit)


class FullProject(EventsProject):
    shop = Slot(FullShopUnit)


AUDIT: t.Final = Permissions({"shop": ShopUnit.Flags.AUDIT})
