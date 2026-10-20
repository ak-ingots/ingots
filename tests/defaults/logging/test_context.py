import asyncio
import logging

from ingots.defaults.logging.context import (
    LogContext,
    LogContextFilter,
    LogContextVar,
    get_log_context,
)

from tests import TestCase

from .logging_fixtures import REQUEST_ID, RUN_ID


class LogContextTestCase(TestCase):
    def test_a_bound_value_is_in_the_context_for_the_block(self) -> None:
        self.assertEqual(get_log_context(), {})
        with REQUEST_ID.bind("outer"):
            with REQUEST_ID.bind("inner"), RUN_ID.bind(7):
                self.assertEqual(
                    get_log_context(), {"test_request_id": "inner", "test_run_id": 7}
                )
            self.assertEqual(get_log_context(), {"test_request_id": "outer"})
        self.assertEqual(get_log_context(), {})

    def test_the_bound_value_is_read_with_or_without_a_default(self) -> None:
        with self.assertRaises(LookupError):
            REQUEST_ID.get()
        self.assertIsNone(REQUEST_ID.get(None))
        with REQUEST_ID.bind("a1"):
            self.assertEqual(REQUEST_ID.get(), "a1")
            self.assertEqual(REQUEST_ID.get(None), "a1")

    def test_a_task_keeps_its_own_value(self) -> None:
        async def handle(request_id: str) -> LogContext:
            with REQUEST_ID.bind(request_id):
                await asyncio.sleep(0)
                return get_log_context()

        async def handle_both() -> tuple[LogContext, LogContext]:
            return await asyncio.gather(handle("a"), handle("b"))

        self.assertEqual(
            list(asyncio.run(handle_both())),
            [{"test_request_id": "a"}, {"test_request_id": "b"}],
        )

    def test_a_name_is_declared_once(self) -> None:
        with self.assertRaisesRegex(ValueError, "'test_request_id' is declared"):
            LogContextVar[str]("test_request_id")
        self.assertEqual(REQUEST_ID.name, "test_request_id")
        self.assertEqual(repr(REQUEST_ID), "LogContextVar('test_request_id')")

    def test_the_context_is_formatted_as_names_and_values(self) -> None:
        self.assertEqual(str(LogContext()), "-")
        self.assertEqual(
            str(LogContext(test_request_id="a1", test_run_id=7)),
            "test_request_id=a1 test_run_id=7",
        )

    def test_the_filter_adds_the_context_to_a_record(self) -> None:
        record = logging.makeLogRecord({"msg": "handled"})
        with REQUEST_ID.bind("a1"):
            self.assertTrue(LogContextFilter().filter(record))
        self.assertEqual(getattr(record, "cvars"), {"test_request_id": "a1"})
