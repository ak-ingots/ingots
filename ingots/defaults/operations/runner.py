"""The runner of the operations: one flow for every run."""

__all__ = ("CALLER_UID", "RUN_UID", "OperationsRunner")

import logging
import typing as t

from ingots.defaults.logging.context import LogContextVar
from ingots.puer import Entity

if t.TYPE_CHECKING:
    from ingots.defaults.project import Project
    from ingots.puer import BoundFactory

    from .operation import BaseOperation, OperationMetadata

logger = logging.getLogger(__name__)

RUN_UID: t.Final = LogContextVar[str]("operation_run_uid")
"""The uid of the run in the log records of an operation."""

CALLER_UID: t.Final = LogContextVar[str]("operation_caller_uid")
"""The uid of the caller in the log records of an operation."""


class OperationsRunner(Entity):
    """
    Runs an operation from its factory, a new instance each time, so that
    runs go on concurrently: the uid of the run and of the caller go into
    the log records, the checker of the project lets the caller run its
    class or refuses, then the factory creates it and the result comes
    back. An operation runs another through
    the runner too, passing its metadata on: the chain logs one run uid,
    and the checker checks the caller for each operation. An exception of
    the operation is raised as it is, logged by its ``repr()``, its message
    and its context, without its traceback: its handler, a policy of a
    server for one, logs it as it decides.
    """

    project: "Project"

    @t.final
    async def run[ParametersType, ResultType](
        self,
        factory: "BoundFactory[BaseOperation[ParametersType, ResultType]]",
        parameters: ParametersType,
        metadata: "OperationMetadata",
    ) -> ResultType:
        """
        Runs the operation ``factory`` creates, ``project.shop.pay``, with
        ``parameters`` for the caller of ``metadata``.

        :raises OperationPermissionsError: the caller may not run it.
        """
        with RUN_UID.bind(metadata.run_uid), CALLER_UID.bind(metadata.caller.uid):
            await self.project.operations.checker.check(factory.cls, metadata)
            operation = factory()
            logger.info("%r: started", operation)
            try:
                result = await operation._run(parameters, metadata)
            except Exception as error:
                logger.info("%r: failed: %r", operation, error)
                raise
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%r: done: %r -> %r", operation, parameters, result)
            else:
                logger.info("%r: done", operation)
        return result

    @t.final
    async def run_safe[ParametersType, ResultType](
        self,
        factory: "BoundFactory[BaseOperation[ParametersType, ResultType]]",
        parameters: ParametersType,
        metadata: "OperationMetadata",
    ) -> ResultType | None:
        """
        Runs the operation as :meth:`run` does, giving ``None`` for its
        result when it fails: for one whose failure must not fail its
        caller, an entry of an activity log for one. Nothing handles the
        exception afterwards, so it is logged at ``WARNING`` with its
        traceback.
        """
        try:
            return await self.run(factory, parameters, metadata)
        except Exception as error:
            logger.warning(
                "<%s>: failure ignored: %r",
                factory.cls.__qualname__,
                error,
                exc_info=error,
            )
            return None
