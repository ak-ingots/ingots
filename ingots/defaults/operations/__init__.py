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

from ingots.puer import Slot, Unit

from .caller import ANONYMOUS_CALLER, ROOT_CALLER, Caller
from .checker import PermissionsChecker
from .errors import OperationPermissionsError
from .operation import BaseOperation, OperationMetadata
from .permissions import PERMISSION_BITS, PermissionFlags, Permissions
from .runner import OperationsRunner


class Operations(Unit):
    """
    The base of the operations, not the operations themselves: those live
    in the units of their domains. ``runner`` runs them, ``checker`` lets
    their callers run them; a subclass of either in its slot changes how.
    """

    checker = Slot(PermissionsChecker)
    runner = Slot(OperationsRunner)

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
