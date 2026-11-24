import asyncio
import gc
import typing as t
import warnings

from ingots.defaults.events import EventsUnit
from ingots.defaults.operations import Caller

from tests import TestCase

from .events_fixtures import AUDIT, EventsProject, FullProject, Paid, ShopUnit

LOGGER = "ingots.defaults.operations"
CUSTOMER: t.Final = Caller(uid="customer")
STAFF: t.Final = Caller(uid="staff", permissions=AUDIT)


class EventsTestCase(TestCase):
    @t.override
    def setUp(self) -> None:
        self.project = EventsProject()
        self.shop: ShopUnit = self.project.shop
        self.events: EventsUnit = self.project.events
        self.metadata = self.project.operations.create_metadata(CUSTOMER)

    def publish(self, amount: int) -> None:
        self.events.publish(self.shop.ev_paid, Paid(amount=amount), self.metadata)


class PublishTestCase(EventsTestCase):
    def test_the_subscribers_run_in_the_background(self) -> None:
        async def flow() -> list[str]:
            self.publish(5)
            seen = list(self.shop.seen)  # the flow goes on first
            await self.events.join()
            return seen

        self.assertEqual(asyncio.run(flow()), [])
        self.assertEqual(self.shop.seen, ["receipt 5"])

    def test_a_subscriber_fails_and_is_refused_alone(self) -> None:
        project = FullProject()

        async def flow() -> None:
            metadata = project.operations.create_metadata(CUSTOMER)
            project.events.publish(project.shop.ev_paid, Paid(amount=5), metadata)
            await project.events.join()

        with self.assertLogs(LOGGER, "WARNING") as logs:
            asyncio.run(flow())
        self.assertEqual(project.shop.seen, ["receipt 5", "label 5"])
        self.assertTrue(
            any("<AuditOperation>: skipped" in line for line in logs.output)
        )
        self.assertTrue(
            any("<BrokenOperation>: failure ignored" in line for line in logs.output)
        )

    def test_the_subscribers_run_for_the_caller_of_the_publisher(self) -> None:
        project = FullProject()

        async def flow() -> None:
            metadata = project.operations.create_metadata(STAFF)
            project.events.publish(project.shop.ev_paid, Paid(amount=5), metadata)
            await project.events.join()

        with self.assertLogs(LOGGER, "WARNING"):
            asyncio.run(flow())
        self.assertCountEqual(project.shop.seen, ["receipt 5", "audit 5", "label 5"])

    def test_the_shutdown_waits_for_the_subscribers(self) -> None:
        project = FullProject()

        async def flow() -> None:
            metadata = project.operations.create_metadata(CUSTOMER)
            project.events.publish(project.shop.ev_paid, Paid(amount=5), metadata)
            await project._do_shut_down()

        with self.assertLogs(LOGGER, "WARNING"):
            asyncio.run(flow())
        self.assertIn("label 5", project.shop.seen)


class HoldTestCase(EventsTestCase):
    def test_a_hold_sends_when_it_ends(self) -> None:
        async def flow() -> list[str]:
            async with self.events.hold():
                self.publish(5)
                await self.events.join()
                held = list(self.shop.seen)
            await self.events.join()
            return held

        self.assertEqual(asyncio.run(flow()), [])
        self.assertEqual(self.shop.seen, ["receipt 5"])

    def test_a_hold_sends_though_its_block_raises(self) -> None:
        async def flow() -> None:
            try:
                async with self.events.hold():
                    self.publish(5)
                    raise RuntimeError("after the change")
            except RuntimeError:
                pass
            await self.events.join()

        asyncio.run(flow())
        self.assertEqual(self.shop.seen, ["receipt 5"])

    def test_a_discard_drops_what_the_scope_holds(self) -> None:
        async def flow() -> None:
            async with self.events.hold() as held:
                self.publish(5)
                held.discard()
                self.publish(6)
            await self.events.join()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            asyncio.run(flow())
            gc.collect()
        self.assertEqual(self.shop.seen, ["receipt 6"])
        # the run dropped is closed: none warns it was never awaited
        self.assertEqual([str(warning.message) for warning in caught], [])

    def test_a_nested_hold_gives_its_events_to_the_outer(self) -> None:
        async def flow() -> list[str]:
            async with self.events.hold():
                async with self.events.hold():
                    self.publish(5)
                await self.events.join()
                held = list(self.shop.seen)
                async with self.events.hold() as inner:
                    self.publish(6)
                    inner.discard()
            await self.events.join()
            return held

        self.assertEqual(asyncio.run(flow()), [])
        self.assertEqual(self.shop.seen, ["receipt 5"])

    def test_the_tasks_of_a_hold_publish_into_it(self) -> None:
        async def flow() -> list[str]:
            async with self.events.hold():
                await asyncio.gather(
                    asyncio.to_thread(lambda: None), self._publish_later(5)
                )
                await self.events.join()
                held = list(self.shop.seen)
            await self.events.join()
            return held

        self.assertEqual(asyncio.run(flow()), [])
        self.assertEqual(self.shop.seen, ["receipt 5"])

    def test_a_task_outliving_its_hold_sends_itself(self) -> None:
        async def flow() -> None:
            async with self.events.hold():
                task = asyncio.create_task(self._publish_later(5))
            await task
            await self.events.join()

        asyncio.run(flow())
        self.assertEqual(self.shop.seen, ["receipt 5"])

    def test_a_hold_in_a_task_outliving_its_outer_sends_itself(self) -> None:
        async def hold_later() -> None:
            await asyncio.sleep(0)
            async with self.events.hold():
                self.publish(5)

        async def flow() -> None:
            async with self.events.hold():
                task = asyncio.create_task(hold_later())
            await task
            await self.events.join()

        asyncio.run(flow())
        self.assertEqual(self.shop.seen, ["receipt 5"])

    def test_a_subscriber_publishes_outside_the_hold_it_was_sent_from(self) -> None:
        project = FullProject()

        async def flow() -> None:
            metadata = project.operations.create_metadata(STAFF)
            async with project.events.hold():
                project.events.publish(project.shop.ev_paid, Paid(amount=5), metadata)
            await project.events.join()

        with self.assertLogs(LOGGER, "WARNING"):
            asyncio.run(flow())
        self.assertIn("label 5", project.shop.seen)

    async def _publish_later(self, amount: int) -> None:
        await asyncio.sleep(0)
        self.publish(amount)


class TransactionTestCase(EventsTestCase):
    def test_a_commit_sends_the_events_of_its_transaction(self) -> None:
        async def flow() -> None:
            async with self.shop.transaction():
                async with self.shop.transaction():  # the same one
                    self.publish(5)
            await self.events.join()

        asyncio.run(flow())
        self.assertEqual(self.shop.seen, ["receipt 5"])

    def test_a_rollback_drops_them(self) -> None:
        async def flow() -> None:
            try:
                async with self.shop.transaction():
                    self.publish(5)
                    raise RuntimeError("rolled back")
            except RuntimeError:
                pass
            await self.events.join()

        asyncio.run(flow())
        self.assertEqual(self.shop.seen, [])

    def test_a_transaction_in_a_hold_sends_by_the_hold(self) -> None:
        async def flow() -> list[str]:
            async with self.events.hold():
                async with self.shop.transaction():
                    self.publish(5)
                await self.events.join()
                held = list(self.shop.seen)
            await self.events.join()
            return held

        self.assertEqual(asyncio.run(flow()), [])
        self.assertEqual(self.shop.seen, ["receipt 5"])
