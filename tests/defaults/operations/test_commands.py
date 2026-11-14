import contextlib
import io
import typing as t
from unittest import mock

from ingots.defaults.operations import BaseOperationCommand, Caller
from ingots.puer import Slot
from ingots.puer.cli import CliUnit, CommandRunner

from tests import TestCase

from .operations_fixtures import (
    PayOperation,
    PayParameters,
    REFUND,
    Receipt,
    ShopProject,
    ShopUnit,
)

if t.TYPE_CHECKING:
    from ingots.puer import BoundFactory

REFUNDER: t.Final = Caller(uid="refunder", permissions=REFUND)


class PayCommand(BaseOperationCommand[PayParameters, Receipt]):
    cli_name = "pay"
    project: "CommandsProject"

    @t.override
    def _get_operation(self) -> "BoundFactory[PayOperation]":
        return self.project.shop.pay

    @t.override
    async def _run(self) -> None:
        receipt = await self.run_operation(PayParameters(5))
        print(receipt.amount, receipt.caller_uid)


class RefunderPayCommand(PayCommand):
    cli_name = "pay-as-refunder"

    @t.override
    def _get_caller(self) -> Caller:
        return REFUNDER


class ShopCommandsUnit(ShopUnit, CliUnit):
    cli_name = "shop"

    cmd_pay = Slot(PayCommand)
    cmd_pay_as_refunder = Slot(RefunderPayCommand)


class CommandsProject(ShopProject):
    shop = Slot(ShopCommandsUnit)


class OperationCommandTestCase(TestCase):
    @t.override
    def setUp(self) -> None:
        # the logging is not under test: keep the handlers of assertLogs
        self.enterContext(mock.patch("logging.config.dictConfig"))

    def run_project(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = CommandRunner(
                CommandsProject, ["--config", "IS_PRINT_CONFIGS=off", *argv]
            ).run()
        return code, out.getvalue()

    def test_the_command_runs_its_operation_as_the_root(self) -> None:
        with self.assertLogs("ingots.defaults.operations", "INFO"):
            self.assertEqual(self.run_project("shop", "pay"), (0, "5 root\n"))

    def test_the_caller_of_the_command_is_its_hook(self) -> None:
        with self.assertLogs("ingots", "INFO") as logs:
            code, out = self.run_project("shop", "pay-as-refunder")
        self.assertEqual((code, out), (1, ""))
        self.assertTrue(any("refunder lacks" in line for line in logs.output))
