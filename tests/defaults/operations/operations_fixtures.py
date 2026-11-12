"""A domain of the operations: a shop paying and refunding."""

import asyncio
import typing as t
from dataclasses import dataclass

from ingots.defaults import Project
from ingots.defaults.operations import (
    BaseOperation,
    OperationMetadata,
    PermissionFlags,
    Permissions,
)
from ingots.defaults.operations.runner import CALLER_UID, RUN_UID
from ingots.puer import Factories, Factory, Slot, Unit


class Shop(PermissionFlags, domain="shop"):
    PAY = 1 << 0
    REFUND = 1 << 1


class Stock(PermissionFlags, domain="stock"):
    READ = 1 << 0


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


class PayOperation(BaseOperation[PayParameters, Receipt]):
    PERMISSIONS = Permissions(Shop.PAY)

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
    """The limit left after a payment: a check of a payment, as the payment."""

    PERMISSIONS = Permissions(Stock.READ)

    @t.override
    async def _run(self, parameters: PayParameters, metadata: OperationMetadata) -> int:
        if parameters.amount > 50:
            raise LimitExceeded("over the limit", parameters.amount)
        return 50 - parameters.amount


class CheckoutOperation(BaseOperation[tuple[PayParameters, ...], list[Receipt]]):
    PERMISSIONS = Permissions()

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


class PingOperation(BaseOperation[None, str]):
    PERMISSIONS = Permissions()

    @t.override
    async def _run(self, parameters: None, metadata: OperationMetadata) -> str:
        return "pong"


class SleepOperation(BaseOperation[None, None]):
    PERMISSIONS = Permissions()

    @t.override
    async def _run(self, parameters: None, metadata: OperationMetadata) -> None:
        await asyncio.sleep(10)


class WaitOperation(BaseOperation[asyncio.Event, str]):
    PERMISSIONS = Permissions()

    @t.override
    async def _run(self, parameters: asyncio.Event, metadata: OperationMetadata) -> str:
        await parameters.wait()
        return "waited"


class SignalOperation(BaseOperation[asyncio.Event, str]):
    PERMISSIONS = Permissions()

    @t.override
    async def _run(self, parameters: asyncio.Event, metadata: OperationMetadata) -> str:
        parameters.set()
        return "signalled"


class CancelledOperation(BaseOperation[asyncio.Event, None]):
    PERMISSIONS = Permissions()

    @t.override
    async def _run(
        self, parameters: asyncio.Event, metadata: OperationMetadata
    ) -> None:
        raise asyncio.CancelledError()


class ShopUnit(Unit):
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
