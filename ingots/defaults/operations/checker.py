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
    caller needs the :attr:`~BaseOperation.PERMISSIONS` of the operation. A
    subclass in the slot ``checker`` decides otherwise in :meth:`_is_allowed`:
    asking a service for one. It checks the class before the runner creates
    an instance: a refused caller costs no operation.
    """

    @t.final
    async def check(
        self,
        operation_cls: "type[BaseOperation[t.Any, t.Any]]",
        metadata: "OperationMetadata",
    ) -> None:
        """
        Lets the caller of ``metadata`` run an ``operation_cls``, or refuses
        it.

        :raises OperationPermissionsError: the caller may not run it.
        :raises TypeError: the operation declares no permissions.
        """
        try:
            required = operation_cls.PERMISSIONS
        except AttributeError:
            raise TypeError(
                f"{operation_cls.__qualname__} declares no PERMISSIONS: "
                f"Permissions() for none"
            ) from None
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
