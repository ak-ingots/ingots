import asyncio
import typing as t

from ingots.defaults.operations import (
    Caller,
    CallersProvider,
    OperationsUnit,
    Permissions,
)
from ingots.puer import Slot

from tests import TestCase

from .operations_fixtures import PayParameters, Shop, ShopProject, Stock


class ShopCallers(CallersProvider):
    """Anyone may pay."""

    @t.override
    def _get_anonymous_permissions(self) -> Permissions:
        return super()._get_anonymous_permissions() | Permissions(Shop.PAY)


class StockCallers(CallersProvider):
    """Anyone may read the stock."""

    @t.override
    def _get_anonymous_permissions(self) -> Permissions:
        return super()._get_anonymous_permissions() | Permissions(Stock.READ)


class AppCallers(ShopCallers, StockCallers):
    pass


class AppOperationsUnit(OperationsUnit):
    callers = Slot(AppCallers)


class AppProject(ShopProject):
    operations = Slot(AppOperationsUnit)


class CallersTestCase(TestCase):
    def test_a_project_has_the_root_and_the_anonymous_one(self) -> None:
        project = ShopProject()
        callers = project.operations.callers
        self.assertTrue(callers.ROOT.is_root)
        self.assertEqual(callers.get_anonymous(), Caller(uid="anonymous"))

    def test_each_subclass_adds_to_what_anyone_may(self) -> None:
        project = AppProject()
        anonymous = project.operations.callers.get_anonymous()
        self.assertEqual(
            anonymous,
            Caller(uid="anonymous", permissions=Permissions(Shop.PAY, Stock.READ)),
        )
        metadata = project.operations.create_metadata(anonymous)
        run = project.operations.run(project.shop.pay, PayParameters(5), metadata)
        with self.assertLogs("ingots.defaults.operations", "INFO"):
            self.assertEqual(asyncio.run(run).caller_uid, "anonymous")
