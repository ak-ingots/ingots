import abc
import asyncio
import logging
import typing as t

from ingots.defaults.operations import (
    ANONYMOUS_CALLER,
    ROOT_CALLER,
    BaseOperation,
    Caller,
    OperationMetadata,
    OperationPermissionsError,
    OperationsUnit,
    Permissions,
    PermissionsChecker,
)
from ingots.defaults import Project
from ingots.defaults.operations.runner import RUN_UID
from ingots.puer import Factory, Slot

from tests import TestCase

from .operations_fixtures import (
    InsufficientFunds,
    PayOperation,
    PayParameters,
    Receipt,
    Shop,
    ShopProject,
    ShopUnit,
)

LOGGER = "ingots.defaults.operations"
PAYER: t.Final = Caller(uid="payer", permissions=Permissions(Shop.PAY))
REFUNDER: t.Final = Caller(uid="refunder", permissions=Permissions(Shop.REFUND))


def create_recording_project(created: list[PayOperation]) -> ShopProject:
    """A project whose shop records every payment it creates in ``created``."""

    class RecordedPay(PayOperation):
        def __init__(self, project: Project) -> None:
            super().__init__(project)
            created.append(self)

    class RecordingShop(ShopUnit):
        pay = Factory(RecordedPay)

    class RecordingProject(ShopProject):
        shop = Slot(RecordingShop)

    return RecordingProject()


class OperationsTestCase(TestCase):
    @t.override
    def setUp(self) -> None:
        self.project = ShopProject()
        self.runner = self.project.operations.runner
        self.create_metadata = self.project.operations.create_metadata


class RunTestCase(OperationsTestCase):
    def test_an_operation_gives_its_result(self) -> None:
        run = self.runner.run(
            self.project.shop.pay, PayParameters(5), self.create_metadata(PAYER)
        )
        with self.assertLogs(LOGGER, "INFO") as logs:
            receipt = asyncio.run(run)
        t.assert_type(receipt, Receipt)
        self.assertEqual((receipt.amount, receipt.caller_uid), (5, "payer"))
        self.assertRegex(receipt.run_uid, r"^[0-9a-f]{32}$")
        self.assertEqual(
            [record.getMessage() for record in logs.records],
            ["<PayOperation>: started", "<PayOperation>: done"],
        )

    def test_the_run_takes_the_uid_of_its_caller(self) -> None:
        metadata = self.create_metadata(PAYER, run_uid="request-1")
        with self.assertLogs(LOGGER, "INFO"):
            receipt = asyncio.run(
                self.runner.run(self.project.shop.pay, PayParameters(5), metadata)
            )
        self.assertEqual(receipt.logged_as, ("request-1", "payer"))

    def test_a_chain_of_operations_is_one_run(self) -> None:
        metadata = self.create_metadata(PAYER)
        payments = (PayParameters(1), PayParameters(2))
        with self.assertLogs(LOGGER, "INFO") as logs:
            receipts = asyncio.run(
                self.runner.run(self.project.shop.checkout, payments, metadata)
            )
        self.assertEqual([receipt.amount for receipt in receipts], [1, 2])
        self.assertEqual(
            {receipt.logged_as for receipt in receipts}, {(metadata.run_uid, "payer")}
        )
        self.assertEqual(
            [record.getMessage() for record in logs.records],
            [
                "<CheckoutOperation>: started",
                *("<PayOperation>: started", "<PayOperation>: done") * 2,
                "<CheckoutOperation>: done",
            ],
        )

    def test_the_caller_is_checked_for_each_operation_of_a_chain(self) -> None:
        run = self.runner.run(
            self.project.shop.checkout,
            (PayParameters(1),),
            self.create_metadata(REFUNDER),
        )
        with self.assertLogs(LOGGER, "INFO") as logs:
            with self.assertRaises(OperationPermissionsError):
                asyncio.run(run)
        self.assertTrue(
            logs.records[-1]
            .getMessage()
            .startswith(
                "<CheckoutOperation>: failed: OperationPermissionsError("
                "'refunder lacks the permissions of the operation', "
                "Caller(uid='refunder'"
            )
        )

    def test_the_run_is_in_the_log_context_for_the_run_only(self) -> None:
        with self.assertLogs(LOGGER, "INFO"):
            receipt = asyncio.run(
                self.runner.run(
                    self.project.shop.pay,
                    PayParameters(5),
                    self.create_metadata(PAYER),
                )
            )
        self.assertEqual(receipt.logged_as, (receipt.run_uid, "payer"))
        self.assertIsNone(RUN_UID.get(None))

    def test_concurrent_runs_have_instances_and_uids_of_their_own(self) -> None:
        created: list[PayOperation] = []
        project = create_recording_project(created)

        async def run_both() -> list[Receipt]:
            return await asyncio.gather(
                *(
                    project.operations.runner.run(
                        project.shop.pay, PayParameters(n), self.create_metadata(PAYER)
                    )
                    for n in (1, 2)
                )
            )

        with self.assertLogs(LOGGER, "INFO"):
            first, second = asyncio.run(run_both())
        self.assertIsNot(*created)
        self.assertEqual((first.amount, second.amount), (1, 2))
        self.assertNotEqual(first.run_uid, second.run_uid)
        self.assertEqual(first.logged_as[0], first.run_uid)

    def test_a_safe_run_gives_the_result(self) -> None:
        with self.assertLogs(LOGGER, "INFO"):
            receipt = asyncio.run(
                self.runner.run_safe(
                    self.project.shop.pay, PayParameters(5), self.create_metadata(PAYER)
                )
            )
        t.assert_type(receipt, Receipt | None)
        self.assertEqual(receipt and receipt.amount, 5)

    def test_a_safe_run_gives_none_for_a_failure_and_logs_it(self) -> None:
        for caller, amount, error in [
            (PAYER, 500, "InsufficientFunds('insufficient funds', 500)"),
            (REFUNDER, 5, "OperationPermissionsError("),
        ]:
            with self.subTest(error), self.assertLogs(LOGGER, "WARNING") as logs:
                result = asyncio.run(
                    self.runner.run_safe(
                        self.project.shop.pay,
                        PayParameters(amount),
                        self.create_metadata(caller),
                    )
                )
                self.assertIsNone(result)
                [ignored] = logs.records
                self.assertTrue(
                    ignored.getMessage().startswith(
                        f"<PayOperation>: failure ignored: {error}"
                    )
                )
                self.assertIsNotNone(ignored.exc_info)

    def test_a_safe_run_is_still_cancelled(self) -> None:
        async def run_cancelled() -> None:
            task = asyncio.create_task(
                self.runner.run_safe(
                    self.project.shop.sleep, None, self.create_metadata(PAYER)
                )
            )
            await asyncio.sleep(0)
            task.cancel()
            await task

        with self.assertLogs(LOGGER, "INFO"):
            with self.assertRaises(asyncio.CancelledError):
                asyncio.run(run_cancelled())

    def test_the_parameters_and_the_result_are_logged_at_debug(self) -> None:
        with self.assertLogs(LOGGER, "DEBUG") as logs:
            asyncio.run(
                self.runner.run(
                    self.project.shop.ping,
                    None,
                    self.create_metadata(ANONYMOUS_CALLER),
                )
            )
        self.assertEqual(
            logs.output[-1],
            "DEBUG:ingots.defaults.operations.runner:"
            "<PingOperation>: done: None -> 'pong'",
        )

    def test_an_exception_is_raised_as_it_is_and_logged_without_traceback(
        self,
    ) -> None:
        run = self.runner.run(
            self.project.shop.pay, PayParameters(500), self.create_metadata(PAYER)
        )
        with self.assertLogs(LOGGER, "INFO") as logs:
            with self.assertRaises(InsufficientFunds):
                asyncio.run(run)
        [_, failed] = logs.records
        self.assertEqual(failed.levelno, logging.INFO)
        self.assertEqual(
            failed.getMessage(),
            "<PayOperation>: failed: InsufficientFunds('insufficient funds', 500)",
        )
        self.assertIsNone(failed.exc_info)


class UnitRunTestCase(OperationsTestCase):
    def test_the_unit_runs_an_operation_with_its_runner(self) -> None:
        operations = self.project.operations
        run = operations.run(
            self.project.shop.pay, PayParameters(5), self.create_metadata(PAYER)
        )
        with self.assertLogs(LOGGER, "INFO") as logs:
            receipt = asyncio.run(run)
        t.assert_type(receipt, Receipt)
        self.assertEqual(receipt.amount, 5)
        self.assertEqual(logs.records[0].getMessage(), "<PayOperation>: started")

    def test_the_unit_runs_an_operation_safely(self) -> None:
        operations = self.project.operations
        run = operations.run_safe(
            self.project.shop.pay, PayParameters(500), self.create_metadata(PAYER)
        )
        with self.assertLogs(LOGGER, "WARNING"):
            result = asyncio.run(run)
        t.assert_type(result, Receipt | None)
        self.assertIsNone(result)


class PermissionsCheckTestCase(OperationsTestCase):
    def test_a_caller_without_the_permissions_is_refused(self) -> None:
        run = self.runner.run(
            self.project.shop.pay, PayParameters(5), self.create_metadata(REFUNDER)
        )
        with self.assertLogs(LOGGER, "INFO") as logs:
            with self.assertRaises(OperationPermissionsError) as raised:
                asyncio.run(run)
        self.assertEqual(raised.exception.caller, REFUNDER)
        self.assertEqual(raised.exception.required, PayOperation.PERMISSIONS)
        self.assertRegex(raised.exception.run_uid, r"^[0-9a-f]{32}$")
        [refused] = logs.output
        self.assertIn(
            "<PayOperation>: refunder lacks Permissions({'shop': 1})", refused
        )

    def test_a_refused_caller_runs_no_operation(self) -> None:
        # the operation is created to ask its permissions, then not run
        created: list[PayOperation] = []
        project = create_recording_project(created)
        run = project.operations.runner.run(
            project.shop.pay, PayParameters(5), self.create_metadata(REFUNDER)
        )
        with self.assertLogs(LOGGER, "INFO") as logs:
            with self.assertRaises(OperationPermissionsError):
                asyncio.run(run)
        self.assertEqual(len(created), 1)
        self.assertFalse(any("started" in line for line in logs.output))

    def test_the_root_runs_any_operation(self) -> None:
        with self.assertLogs(LOGGER, "INFO"):
            receipt = asyncio.run(
                self.runner.run(
                    self.project.shop.pay,
                    PayParameters(5),
                    self.create_metadata(ROOT_CALLER),
                )
            )
        self.assertEqual(receipt.caller_uid, "root")

    def test_an_operation_requiring_none_runs_for_anyone(self) -> None:
        with self.assertLogs(LOGGER, "INFO"):
            pong = asyncio.run(
                self.runner.run(
                    self.project.shop.ping,
                    None,
                    self.create_metadata(ANONYMOUS_CALLER),
                )
            )
        self.assertEqual(pong, "pong")

    def test_the_hook_gives_the_constant_by_default(self) -> None:
        operation = self.project.shop.pay()
        self.assertIs(operation.get_permissions(), PayOperation.PERMISSIONS)

    def test_the_permissions_come_by_the_hook_of_the_operation(self) -> None:
        class RefundOperation(BaseOperation[int, int]):
            project: "RefundProject"

            @t.override
            def _get_permissions(self) -> Permissions:
                return Permissions(Shop.REFUND) | self.project.EXTRA

            @t.override
            async def _run(self, parameters: int, metadata: OperationMetadata) -> int:
                return -parameters

        class RefundUnit(ShopUnit):
            refund = Factory(RefundOperation)

        class RefundProject(ShopProject):
            EXTRA: t.ClassVar[Permissions] = Permissions()
            shop = Slot(RefundUnit)

        project = RefundProject()
        runner = project.operations.runner
        metadata = project.operations.create_metadata
        with self.assertLogs(LOGGER, "INFO"):
            refunded = asyncio.run(
                runner.run(project.shop.refund, 5, metadata(REFUNDER))
            )
        self.assertEqual(refunded, -5)
        RefundProject.EXTRA = Permissions(Shop.PAY)
        with (
            self.assertLogs(LOGGER, "INFO"),
            self.assertRaises(OperationPermissionsError) as raised,
        ):
            asyncio.run(runner.run(project.shop.refund, 5, metadata(REFUNDER)))
        self.assertEqual(dict(raised.exception.required), {"shop": 3})


class DeclarationTestCase(TestCase):
    def test_an_operation_declares_its_permissions_when_created(self) -> None:
        with self.assertRaisesRegex(
            TypeError, "UndeclaredOperation declares no PERMISSIONS"
        ):

            class UndeclaredOperation(BaseOperation[None, None]):
                @t.override
                async def _run(
                    self, parameters: None, metadata: OperationMetadata
                ) -> None:
                    pass

    def test_a_base_with_an_abstract_method_left_is_not_checked(self) -> None:
        class BaseRefundOperation(BaseOperation[None, None]):
            @abc.abstractmethod
            def _get_reason(self) -> str:
                raise NotImplementedError

            @t.override
            async def _run(self, parameters: None, metadata: OperationMetadata) -> None:
                pass

        with self.assertRaisesRegex(TypeError, "DamagedRefundOperation declares no"):

            class DamagedRefundOperation(BaseRefundOperation):
                @t.override
                def _get_reason(self) -> str:
                    return "damaged"


class CustomizationTestCase(TestCase):
    def test_the_checker_is_replaced_in_its_slot(self) -> None:
        class AllowingChecker(PermissionsChecker):
            @t.override
            async def _is_allowed(
                self,
                operation_cls: type[BaseOperation[t.Any, t.Any]],
                required: Permissions,
                metadata: OperationMetadata,
            ) -> bool:
                return True

        class AppOperationsUnit(OperationsUnit):
            checker = Slot(AllowingChecker)

        class AppProject(ShopProject):
            operations = Slot(AppOperationsUnit)

        project = AppProject()
        run = project.operations.runner.run(
            project.shop.pay,
            PayParameters(5),
            project.operations.create_metadata(ANONYMOUS_CALLER),
        )
        with self.assertLogs(LOGGER, "INFO"):
            receipt = asyncio.run(run)
        self.assertEqual(receipt.caller_uid, "anonymous")

    def test_the_uid_of_a_run_is_created_by_the_unit(self) -> None:
        class AppOperationsUnit(OperationsUnit):
            @t.override
            def create_run_uid(self) -> str:
                return "run-1"

        class AppProject(ShopProject):
            operations = Slot(AppOperationsUnit)

        metadata = AppProject().operations.create_metadata(ANONYMOUS_CALLER)
        self.assertEqual(
            metadata, OperationMetadata(caller=ANONYMOUS_CALLER, run_uid="run-1")
        )
