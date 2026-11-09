"""The operation: a brick of the business logic."""

__all__ = ("BaseOperation", "OperationMetadata")

import abc
import typing as t
from dataclasses import dataclass

from ingots.puer import Entity

if t.TYPE_CHECKING:
    from .caller import Caller
    from .permissions import Permissions


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


class BaseOperation[ParametersType, ResultType](Entity):
    """
    A brick of the business logic, called from handlers, commands, views:
    it takes parameters and gives a result, raising the exceptions of the
    business logic as they are. A unit of its domain declares it as a
    :class:`~ingots.puer.Factory`, and the runner of the operations runs it,
    a new instance for each run::

        class PayOperation(BaseOperation[PayParameters, Receipt]):
            PERMISSIONS = Permissions(ShopUnit.PAY)

            @t.override
            async def _run(self, parameters, metadata):
                ...


        class ShopUnit(Unit):
            pay = Factory(PayOperation)


        receipt = await project.operations.run(
            project.shop.pay,
            parameters,
            project.operations.create_metadata(caller, run_uid=request_id),
        )

    What a caller needs to run it is :meth:`get_permissions`: the constant
    :attr:`PERMISSIONS` by default, ``Permissions()`` for none, one instance
    a process, readable from the class. An operation whose permissions
    depend on its project overrides :meth:`_get_permissions` instead,
    computed on every run. A complete operation does one or the other,
    checked when its class is created.

    :raises TypeError: a complete operation declares neither.
    """

    PERMISSIONS: t.ClassVar["Permissions"]

    @t.override
    @classmethod
    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        _check_permissions(cls)

    @t.override
    def __repr__(self) -> str:
        return f"<{type(self).__qualname__}>"

    @t.final
    def get_permissions(self) -> "Permissions":
        """What a caller needs to run the operation: the runner checks it."""
        return self._get_permissions()

    def _get_permissions(self) -> "Permissions":
        """The constant of the class; an operation needing more overrides it."""
        return self.PERMISSIONS

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


def _check_permissions(cls: "type[BaseOperation[t.Any, t.Any]]") -> None:
    # once, when the class is created: a class with an abstract method left
    # is a base, completed by its subclasses, which are checked in turn
    complete = not any(
        getattr(getattr(cls, name, None), "__isabstractmethod__", False)
        for name in dir(cls)
    )
    overridden = cls._get_permissions is not BaseOperation._get_permissions
    if complete and not overridden and not hasattr(cls, "PERMISSIONS"):
        raise TypeError(
            f"{cls.__qualname__} declares no PERMISSIONS: Permissions() for "
            f"none, or _get_permissions()"
        )
