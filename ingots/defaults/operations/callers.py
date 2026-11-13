"""The callers: who runs an operation, and those every project has."""

__all__ = ("ANONYMOUS_CALLER", "ROOT_CALLER", "Caller", "CallersProvider")

import typing as t
from dataclasses import dataclass

from ingots.puer import Entity

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


class CallersProvider(Entity):
    """
    The callers every project has, the slot ``callers`` of the operations:
    the root, :attr:`ROOT`, running any operation, a command of the operator
    for one; the anonymous one, :meth:`get_anonymous`, of a call that tells
    no one, with what anyone may, :meth:`_get_anonymous_permissions`, nothing
    here. An application or an addon adds to it in a subclass, each to what
    its base gives, so that none takes away what another gave::

        class AppCallers(CallersProvider):
            @t.override
            def _get_anonymous_permissions(self) -> Permissions:
                anyone = Permissions(Catalog.READ)
                return super()._get_anonymous_permissions() | anyone
    """

    ROOT: t.ClassVar[Caller] = Caller(uid="root", is_root=True)

    @t.final
    def get_anonymous(self) -> Caller:
        """The caller of a call that tells no one, with what anyone may."""
        return Caller(uid="anonymous", permissions=self._get_anonymous_permissions())

    def _get_anonymous_permissions(self) -> Permissions:
        """What anyone may: nothing here, a subclass adding to its base."""
        return Permissions()


ANONYMOUS_CALLER: t.Final = Caller(uid="anonymous")
"""
A caller without permissions.

.. deprecated:: 0.33.2
   ``operations.callers.get_anonymous()``, with what the application gives
   anyone; removed in 0.34.
"""

ROOT_CALLER: t.Final = CallersProvider.ROOT
"""
A caller running any operation: a command of the administrator, a test.

.. deprecated:: 0.33.2
   ``operations.callers.ROOT``; removed in 0.34.
"""
