"""
The test suite. ``INGOTS_TEST_LOG=<level>`` (``DEBUG``, ``INFO``, ...) shows the
logs of the run on stderr, those captured by :meth:`TestCase.assertLogs` too.
Without it, the logs of a test that configures the logging are dropped.
"""

__all__ = ("TestCase",)

import contextlib
import io
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
    """
    Restores the logging after every test: configuring a project configures
    the logging of the process. Shows the captured logs as well when
    ``INGOTS_TEST_LOG`` is set.
    """

    def run(
        self, result: unittest.TestResult | None = None
    ) -> unittest.TestResult | None:
        with preserve_logging():
            return super().run(result)

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


@contextlib.contextmanager
def preserve_logging() -> "Iterator[None]":
    """
    Restores the loggers as they were: their levels, handlers, propagation
    and disabling. Handlers created inside write to a dropped buffer unless
    ``INGOTS_TEST_LOG`` is set.
    """
    manager = logging.Logger.manager
    loggers = [logging.root, *manager.loggerDict.values()]
    saved = [
        (logger, logger.level, logger.handlers[:], logger.propagate, logger.disabled)
        for logger in loggers
        if isinstance(logger, logging.Logger)
    ]
    known = {logger.name for logger, *_ in saved}  # not the placeholders
    with contextlib.ExitStack() as stack:
        if not LOG_LEVEL:
            stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
        try:
            yield
        finally:
            for name in set(manager.loggerDict) - known:
                logger = manager.loggerDict[name]
                if isinstance(logger, logging.Logger):
                    logger.setLevel(logging.NOTSET)
                    logger.handlers[:] = []
                    logger.propagate, logger.disabled = True, False
            for logger, level, handlers, propagate, disabled in saved:
                logger.setLevel(level)
                logger.handlers[:] = handlers
                logger.propagate, logger.disabled = propagate, disabled
