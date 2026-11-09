"""The checker of the permissions: whether a caller may run an operation."""

__all__ = ("PermissionsChecker",)

import logging
import typing as t

from ingots.puer import Entity

from .errors import OperationPermissionsError

if t.TYPE_CHECKING:
    from .operation import BaseOperation, OperationMetadata
    from .permissions import Permissions

logger = logging.getLogger(__name__)


class PermissionsChecker(Entity):
    """
    Whether a caller may run an operation: the root runs any, another
    caller needs what the operation requires, its
    :meth:`~BaseOperation.get_permissions`, which the runner asks it and
    passes on. A subclass in the slot ``checker`` decides otherwise in
    :meth:`_is_allowed`: asking a service for one.
    """

    @t.final
    async def check(
        self,
        operation_cls: "type[BaseOperation[t.Any, t.Any]]",
        required: "Permissions",
        metadata: "OperationMetadata",
    ) -> None:
        """
        Lets the caller of ``metadata`` run an ``operation_cls`` requiring
        ``required``, or refuses it.

        :raises OperationPermissionsError: the caller may not run it.
        """
        if metadata.caller.is_root:
            return
        if not await self._is_allowed(operation_cls, required, metadata):
            logger.info(
                "<%s>: %s lacks %r",
                operation_cls.__qualname__,
                metadata.caller.uid,
                required,
            )
            raise OperationPermissionsError.for_caller(
                metadata.caller, metadata.run_uid, required
            )

    async def _is_allowed(
        self,
        operation_cls: "type[BaseOperation[t.Any, t.Any]]",
        required: "Permissions",
        metadata: "OperationMetadata",
    ) -> bool:
        """Whether a caller other than the root may run the operation."""
        return metadata.caller.permissions.has(required)
