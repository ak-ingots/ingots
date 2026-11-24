"""
The operations: the bricks of the business logic, run with the permissions
of their caller.
"""

__all__ = (
    "PERMISSION_BITS",
    "BaseOperation",
    "BaseOperationCommand",
    "BoundPermissions",
    "Caller",
    "CallersProvider",
    "OperationMetadata",
    "OperationPermissionsError",
    "OperationsOwner",
    "OperationsResults",
    "OperationsUnit",
    "OperationsRunner",
    "PermissionFlags",
    "Permissions",
    "PermissionsChecker",
    "PermissionsSlot",
)

import os
import typing as t

from ingots.puer import Slot, Unit

from .callers import Caller, CallersProvider
from .checker import PermissionsChecker
from .commands import BaseOperationCommand
from .errors import OperationPermissionsError
from .operation import BaseOperation, OperationMetadata, OperationsOwner
from .permissions import (
    PERMISSION_BITS,
    BoundPermissions,
    PermissionFlags,
    Permissions,
    PermissionsSlot,
)
from .results import OperationsResults
from .runner import OperationsRunner

if t.TYPE_CHECKING:
    from ingots.puer import BoundFactories, BoundFactory


class OperationsUnit(Unit):
    """
    The base of the operations, not the operations themselves: those live
    in the units of their domains. :meth:`run` runs them with ``runner``,
    :meth:`run_all_in_group` several of them as a whole,
    :meth:`run_each_in_group` several each on its own,
    ``checker`` lets their callers run them, ``callers`` gives those every
    project has, the root and the anonymous one; a subclass of any in its
    slot changes how.
    """

    callers = Slot(CallersProvider)
    checker = Slot(PermissionsChecker)
    runner = Slot(OperationsRunner)

    @t.final
    async def run[ParametersType, ResultType](
        self,
        factory: "BoundFactory[BaseOperation[ParametersType, ResultType]]",
        parameters: ParametersType,
        metadata: OperationMetadata,
    ) -> ResultType:
        """
        Runs the operation ``factory`` creates, ``project.shop.pay``, with
        ``parameters`` for the caller of ``metadata``, as
        :meth:`OperationsRunner.run` does.

        :raises OperationPermissionsError: the caller may not run it.
        """
        return await self.runner.run(factory, parameters, metadata)

    @t.final
    async def run_safe[ParametersType, ResultType](
        self,
        factory: "BoundFactory[BaseOperation[ParametersType, ResultType]]",
        parameters: ParametersType,
        metadata: OperationMetadata,
    ) -> ResultType | None:
        """
        Runs the operation, giving ``None`` for its result when it fails, as
        :meth:`OperationsRunner.run_safe` does.
        """
        return await self.runner.run_safe(factory, parameters, metadata)

    @t.final
    async def run_all_in_group[ParametersType](
        self,
        factories: "BoundFactories[BaseOperation[ParametersType, t.Any]]",
        parameters: ParametersType,
        metadata: OperationMetadata,
    ) -> OperationsResults:
        """
        Runs the operations ``factories`` creates, ``project.shop.checks``,
        as a whole, each with ``parameters``, as
        :meth:`OperationsRunner.run_all_in_group` does.

        :raises OperationPermissionsError: the caller may not run one; none
            runs.
        :raises ExceptionGroup: some failed.
        """
        return await self.runner.run_all_in_group(factories, parameters, metadata)

    @t.final
    async def run_each_in_group[ParametersType](
        self,
        factories: "BoundFactories[BaseOperation[ParametersType, t.Any]]",
        parameters: ParametersType,
        metadata: OperationMetadata,
    ) -> None:
        """
        Runs the operations ``factories`` creates, each on its own, with
        ``parameters``, as :meth:`OperationsRunner.run_each_in_group` does:
        a refusal and a failure logged, none raised.
        """
        await self.runner.run_each_in_group(factories, parameters, metadata)

    def create_metadata(
        self, caller: Caller, *, run_uid: str | None = None
    ) -> OperationMetadata:
        """
        The metadata of a new run for ``caller``: ``run_uid`` is the id of
        its request, tying the logs of the client and of the server; without
        one, the run takes a new uid.
        """
        if run_uid is None:
            run_uid = self.create_run_uid()
        return OperationMetadata(caller=caller, run_uid=run_uid)

    def create_run_uid(self) -> str:
        """The uid of a new run: 128 random bits, 32 hexadecimal digits."""
        return os.urandom(16).hex()
