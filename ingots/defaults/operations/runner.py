"""The runner of the operations: one flow for every run."""

__all__ = ("CALLER_UID", "RUN_UID", "OperationsRunner")

import asyncio
import logging
import typing as t

from ingots.defaults.logging.context import LogContextVar
from ingots.puer import Entity

from .results import OperationsResults

if t.TYPE_CHECKING:
    from ingots.defaults.project import Project
    from ingots.puer import BoundFactories, BoundFactory

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
    the log records, the factory creates the operation, the checker of the
    project lets the caller run it or refuses, by what the operation
    requires, its :meth:`~BaseOperation.get_permissions`, then the result
    comes back. A refused caller costs an instance, of nothing but a weak
    reference to the project. An operation runs another through
    the runner too, passing its metadata on: the chain logs one run uid,
    and the checker checks the caller for each operation. An exception of
    the operation is raised as it is, logged by its ``repr()``, its message
    and its context, without its traceback: its handler, a policy of a
    server for one, logs it as it decides.

    Operations independent of each other, taking the same parameters, run
    together from the slot of their factories, :meth:`run_group`.
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
            operation = factory()
            await self.project.operations.checker.check(
                factory.cls, operation.get_permissions(), metadata
            )
            return await self._run_operation(operation, parameters, metadata)

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

    @t.final
    async def run_group[ParametersType](
        self,
        factories: "BoundFactories[BaseOperation[ParametersType, t.Any]]",
        parameters: ParametersType,
        metadata: "OperationMetadata",
    ) -> OperationsResults:
        """
        Runs the operations ``factories`` creates, ``project.shop.checks``,
        concurrently, each with ``parameters`` for the caller of
        ``metadata``: the caller is checked for every one before any runs,
        and every one runs to its end, whatever the others do. The context
        of the logs is bound once for them all.

        :raises OperationPermissionsError: the caller may not run one; none
            runs.
        :raises ExceptionGroup: some failed, their exceptions in the order
            of their classes.
        """
        with RUN_UID.bind(metadata.run_uid), CALLER_UID.bind(metadata.caller.uid):
            operations = factories()
            checker = self.project.operations.checker
            for operation in operations:
                await checker.check(
                    type(operation), operation.get_permissions(), metadata
                )
            outcomes = await asyncio.gather(
                *(
                    self._run_operation(operation, parameters, metadata)
                    for operation in operations
                ),
                return_exceptions=True,
            )
        errors: list[Exception] = []
        for outcome in outcomes:
            if isinstance(outcome, Exception):
                errors.append(outcome)
            elif isinstance(outcome, BaseException):
                raise outcome  # a cancellation goes through, not a failure
        if errors:
            raise ExceptionGroup(
                f"{len(errors)} of {len(operations)} operations failed", errors
            )
        return OperationsResults(dict(zip(factories.classes, outcomes)))

    @t.final
    async def _run_operation[ParametersType, ResultType](
        self,
        operation: "BaseOperation[ParametersType, ResultType]",
        parameters: ParametersType,
        metadata: "OperationMetadata",
    ) -> ResultType:
        # an operation created, its caller checked, the context of the logs
        # bound: what every run shares
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
