"""
A domain of the operations: a shop paying and refunding, with its stock, each
a unit binding its permissions, their domains ``shop`` and ``shop.stock``.
"""

import asyncio
import typing as t
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
from ingots.defaults.operations.runner import CALLER_UID, RUN_UID
from ingots.puer import Factories, Factory, Slot, Unit


@dataclass(frozen=True)
class PayParameters:
    amount: int


@dataclass(frozen=True)
class Receipt:
    amount: int
    run_uid: str
    caller_uid: str
    logged_as: tuple[str, str]


class InsufficientFunds(Exception):
    pass


class LimitExceeded(Exception):
    pass


class OpenOperation[ParametersType, ResultType](
    BaseOperation[ParametersType, ResultType]
):
    """An operation anyone may run."""

    @t.override
    def _get_permissions(self) -> Permissions:
        return Permissions()


class PayOperation(BaseOperation[PayParameters, Receipt]):
    parent: "ShopUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.PAY)

    @t.override
    async def _run(
        self, parameters: PayParameters, metadata: OperationMetadata
    ) -> Receipt:
        if parameters.amount > 100:
            raise InsufficientFunds("insufficient funds", parameters.amount)
        return Receipt(
            parameters.amount,
            metadata.run_uid,
            metadata.caller.uid,
            (RUN_UID.get(), CALLER_UID.get()),
        )


class LimitOperation(BaseOperation[PayParameters, int]):
    """
    The limit left after a payment: a check of a payment, as the payment,
    of the reading of the stock.
    """

    parent: "ShopUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.stock.permissions
        return permissions(permissions.flags.READ)

    @t.override
    async def _run(self, parameters: PayParameters, metadata: OperationMetadata) -> int:
        if parameters.amount > 50:
            raise LimitExceeded("over the limit", parameters.amount)
        return 50 - parameters.amount


class CheckoutOperation(OpenOperation[tuple[PayParameters, ...], list[Receipt]]):
    project: "ShopProject"

    @t.override
    async def _run(
        self, parameters: tuple[PayParameters, ...], metadata: OperationMetadata
    ) -> list[Receipt]:
        operations = self.project.operations
        return [
            await operations.run(self.project.shop.pay, payment, metadata)
            for payment in parameters
        ]


class PingOperation(OpenOperation[None, str]):
    @t.override
    async def _run(self, parameters: None, metadata: OperationMetadata) -> str:
        return "pong"


class SleepOperation(OpenOperation[None, None]):
    @t.override
    async def _run(self, parameters: None, metadata: OperationMetadata) -> None:
        await asyncio.sleep(10)


class WaitOperation(OpenOperation[asyncio.Event, str]):
    @t.override
    async def _run(self, parameters: asyncio.Event, metadata: OperationMetadata) -> str:
        await parameters.wait()
        return "waited"


class SignalOperation(OpenOperation[asyncio.Event, str]):
    @t.override
    async def _run(self, parameters: asyncio.Event, metadata: OperationMetadata) -> str:
        parameters.set()
        return "signalled"


class CancelledOperation(OpenOperation[asyncio.Event, None]):
    @t.override
    async def _run(
        self, parameters: asyncio.Event, metadata: OperationMetadata
    ) -> None:
        raise asyncio.CancelledError()


class StockUnit(OperationsOwner, Unit):
    class Flags(PermissionFlags):
        READ = 1 << 0

    permissions = PermissionsSlot(Flags)


class ShopUnit(OperationsOwner, Unit):
    class Flags(PermissionFlags):
        PAY = 1 << 0
        REFUND = 1 << 1

    permissions = PermissionsSlot(Flags)

    stock = Slot(StockUnit)

    pay = Factory(PayOperation)
    checkout = Factory(CheckoutOperation)
    ping = Factory(PingOperation)
    sleep = Factory(SleepOperation)
    # a payment with its checks; a group waiting for itself
    checks = Factories[BaseOperation[PayParameters, t.Any]](
        PayOperation, LimitOperation
    )
    handshake = Factories[BaseOperation[asyncio.Event, t.Any]](
        WaitOperation, SignalOperation
    )


class ShopProject(Project):
    shop = Slot(ShopUnit)


# the masks of the callers, by the domains of the units of the project
PAY: t.Final = Permissions({"shop": ShopUnit.Flags.PAY})
REFUND: t.Final = Permissions({"shop": ShopUnit.Flags.REFUND})
READ: t.Final = Permissions({"shop.stock": StockUnit.Flags.READ})
