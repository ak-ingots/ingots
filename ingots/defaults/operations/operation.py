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

        class Pay(BaseOperation[PayParameters, Receipt]):
            PERMISSIONS = Permissions(Shop.PAY)

            @t.override
            async def _run(self, parameters, metadata):
                ...


        class Shop(Unit):
            pay = Factory(Pay)


        receipt = await project.operations.run(
            project.shop.pay,
            parameters,
            project.operations.create_metadata(caller, run_uid=request_id),
        )

    :attr:`PERMISSIONS` are those a caller needs to run it,
    ``Permissions()`` for none: an operation declares them, even empty.
    """

    PERMISSIONS: t.ClassVar["Permissions"]

    @t.override
    def __repr__(self) -> str:
        return f"<{type(self).__qualname__}>"

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
