"""The operation: a brick of the business logic, and the units owning them."""

__all__ = ("BaseOperation", "OperationMetadata", "OperationsOwner")

import abc
import typing as t
from dataclasses import dataclass

from ingots.puer import Entity

if t.TYPE_CHECKING:
    from .callers import Caller
    from .permissions import Permissions, PermissionsSlot


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationMetadata:
    """
    What a run of operations knows besides its parameters: who calls them
    and the uid of the run. Its caller, a handler of a request for one,
    creates it with ``project.operations.create_metadata()``, giving the id
    of the request as the uid of the run. An operation passes it on to the
    operations it runs: a chain of them is one run.
    """

    caller: "Caller"
    run_uid: str


class OperationsOwner(Entity):
    """
    A mixin of a unit owning operations, which are not its base: its slot
    ``permissions``, a :class:`~.PermissionsSlot`, binds the flags of their
    permissions, nested in it or next to it, their domain its full name::

        class ShopUnit(OperationsOwner, Unit):
            class Flags(PermissionFlags):
                PAY = 1 << 0

            permissions = PermissionsSlot(Flags)

            pay = Factory(PayOperation)
    """

    permissions: "PermissionsSlot[t.Any]"


class BaseOperation[ParametersType, ResultType](Entity):
    """
    A brick of the business logic, called from handlers, commands, views:
    it takes parameters and gives a result, raising the exceptions of the
    business logic as they are. A unit of its domain declares it as a
    :class:`~ingots.puer.Factory`, and the runner of the operations runs it,
    a new instance for each run::

        class PayOperation(BaseOperation[PayParameters, Receipt]):
            parent: "ShopUnit"

            @t.override
            def _get_permissions(self) -> Permissions:
                permissions = self.parent.permissions
                return permissions(permissions.flags.PAY)

            @t.override
            async def _run(self, parameters, metadata):
                ...


        receipt = await project.operations.run(
            project.shop.pay,
            parameters,
            project.operations.create_metadata(caller, run_uid=request_id),
        )

    What a caller needs to run it is :meth:`get_permissions`, of its hook
    :meth:`_get_permissions`, abstract: it builds them by the permissions of
    the unit it reaches, its parent narrowed, or the nearest of a kind,
    ``self.find_parent(ShopUnit)``, so that mypy checks the flags, of the
    enum of that unit, and the hook itself, an operation forgetting it
    abstract, refused where a factory takes it; ``Permissions()`` for none.
    An operation running others of other domains adds their permissions,
    not their flags: ``self.parent.stock.op_move().get_permissions()``.
    """

    @t.override
    def __repr__(self) -> str:
        return f"<{type(self).__qualname__}>"

    @t.final
    def get_permissions(self) -> "Permissions":
        """What a caller needs to run the operation: the runner checks it."""
        return self._get_permissions()

    @abc.abstractmethod
    def _get_permissions(self) -> "Permissions":
        """What a caller needs, built by the permissions of a unit."""
        raise NotImplementedError(f"{type(self).__qualname__}._get_permissions")

    @abc.abstractmethod
    async def _run(
        self, parameters: ParametersType, metadata: OperationMetadata
    ) -> ResultType:
        """
        Runs the operation: called once, by the runner of the operations.
        Another operation it needs runs through the runner too, with the
        same ``metadata``.
        """
        raise NotImplementedError(f"{type(self).__qualname__}._run")
