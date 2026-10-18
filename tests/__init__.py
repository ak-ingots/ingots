"""
The test suite. ``INGOTS_TEST_LOG=<level>`` (``DEBUG``, ``INFO``, ...) shows the
logs of the run on stderr, those captured by :meth:`TestCase.assertLogs` too.
"""

__all__ = ("TestCase",)

import contextlib
import logging
import os
import typing as t
import unittest

if t.TYPE_CHECKING:
    from collections.abc import Iterator

LOG_LEVEL = os.environ.get("INGOTS_TEST_LOG", "").upper()

if LOG_LEVEL:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(relativeCreated)6.0fms %(levelname)-7s %(name)s: %(message)s",
    )


class TestCase(unittest.TestCase):
    """Shows the captured logs as well when ``INGOTS_TEST_LOG`` is set."""

    @contextlib.contextmanager
    def assertLogs(  # type: ignore[override]
        self,
        logger: str | logging.Logger | None = None,
        level: int | str | None = None,
    ) -> "Iterator[unittest._log._LoggingWatcher]":
        with super().assertLogs(logger, level) as watcher:
            yield watcher
        if LOG_LEVEL:
            for record in watcher.records:
                logging.getLogger(record.name).handle(record)
