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
from ingots.puer import Factory, Slot, Unit


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


class Pay(BaseOperation[PayParameters, Receipt]):
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


class Checkout(BaseOperation[tuple[PayParameters, ...], list[Receipt]]):
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


class Ping(BaseOperation[None, str]):
    PERMISSIONS = Permissions()

    @t.override
    async def _run(self, parameters: None, metadata: OperationMetadata) -> str:
        return "pong"


class Sleep(BaseOperation[None, None]):
    PERMISSIONS = Permissions()

    @t.override
    async def _run(self, parameters: None, metadata: OperationMetadata) -> None:
        await asyncio.sleep(10)


class Undeclared(BaseOperation[None, None]):
    @t.override
    async def _run(self, parameters: None, metadata: OperationMetadata) -> None:
        pass


class ShopUnit(Unit):
    pay = Factory(Pay)
    checkout = Factory(Checkout)
    ping = Factory(Ping)
    sleep = Factory(Sleep)
    undeclared = Factory(Undeclared)


class ShopProject(Project):
    shop = Slot(ShopUnit)
