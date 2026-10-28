"""
The operations: the bricks of the business logic, run with the permissions
of their caller.
"""

__all__ = (
    "ANONYMOUS_CALLER",
    "PERMISSION_BITS",
    "ROOT_CALLER",
    "BaseOperation",
    "Caller",
    "OperationMetadata",
    "OperationPermissionsError",
    "Operations",
    "OperationsRunner",
    "PermissionFlags",
    "Permissions",
    "PermissionsChecker",
)

import os
import typing as t

from ingots.puer import Slot, Unit

from .caller import ANONYMOUS_CALLER, ROOT_CALLER, Caller
from .checker import PermissionsChecker
from .errors import OperationPermissionsError
from .operation import BaseOperation, OperationMetadata
from .permissions import PERMISSION_BITS, PermissionFlags, Permissions
from .runner import OperationsRunner

if t.TYPE_CHECKING:
    from ingots.puer import BoundFactory


class Operations(Unit):
    """
    The base of the operations, not the operations themselves: those live
    in the units of their domains. :meth:`run` runs them with ``runner``,
    ``checker`` lets their callers run them; a subclass of either in its
    slot changes how.
    """

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
