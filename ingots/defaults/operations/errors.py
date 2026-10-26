"""The errors of the operations."""

__all__ = ("OperationPermissionsError",)

import typing as t

if t.TYPE_CHECKING:
    from .caller import Caller
    from .permissions import Permissions


class OperationPermissionsError(Exception):
    """
    The caller lacks the permissions an operation requires. ``args`` are the
    message, the caller, the uid of the run and the permissions required,
    so the error survives pickling; create it with :meth:`for_caller`.
    """

    @classmethod
    def for_caller(
        cls, caller: "Caller", run_uid: str, required: "Permissions"
    ) -> t.Self:
        """The error of a caller lacking ``required``."""
        return cls(
            f"{caller.uid} lacks the permissions of the operation",
            caller,
            run_uid,
            required,
        )

    @property
    def caller(self) -> "Caller":
        """The caller refused."""
        return t.cast("Caller", self.args[1])

    @property
    def run_uid(self) -> str:
        """The uid of the refused run."""
        return t.cast(str, self.args[2])

    @property
    def required(self) -> "Permissions":
        """The permissions the operation requires."""
        return t.cast("Permissions", self.args[3])

    @t.override
    def __str__(self) -> str:
        return t.cast(str, self.args[0])
