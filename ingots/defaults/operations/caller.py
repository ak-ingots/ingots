"""The caller: who runs an operation."""

__all__ = ("ANONYMOUS_CALLER", "ROOT_CALLER", "Caller")

import typing as t
from dataclasses import dataclass

from .permissions import Permissions


@dataclass(frozen=True, slots=True, kw_only=True)
class Caller:
    """
    Who runs an operation: a user, a service, a command, with its
    permissions; ``is_root`` runs any operation. Immutable: a caller with
    other permissions is another caller,
    ``dataclasses.replace(caller, permissions=...)``.
    """

    uid: str
    permissions: Permissions = Permissions()
    is_root: bool = False


ANONYMOUS_CALLER: t.Final = Caller(uid="anonymous")
"""A caller without permissions."""

ROOT_CALLER: t.Final = Caller(uid="root", is_root=True)
"""A caller running any operation: a command of the administrator, a test."""
