"""The base of the commands that run an operation."""

__all__ = ("BaseOperationCommand",)

import abc
import typing as t

from ingots.puer.cli import BaseCommand

from .caller import ROOT_CALLER

if t.TYPE_CHECKING:
    from ingots.defaults.project import Project
    from ingots.puer import BoundFactory

    from .caller import Caller
    from .operation import BaseOperation


class BaseOperationCommand[ParametersType, ResultType](BaseCommand):
    """
    A command running an operation, which a subclass gives in
    :meth:`_get_operation`, for the caller of :meth:`_get_caller`, the root
    by default, the command line being the operator's. Its ``_run`` calls
    :meth:`run_operation` and does what it needs with the result::

        class ListTagsCommand(BaseOperationCommand[None, tuple[Tag, ...]]):
            cli_name = "list"

            @t.override
            def _get_operation(self) -> "BoundFactory[ListTags]":
                return self.project.tags.op_list

            @t.override
            async def _run(self) -> None:
                for tag in await self.run_operation(None):
                    print(tag.name)
    """

    project: "Project"

    @t.final
    async def run_operation(self, parameters: ParametersType) -> ResultType:
        """Runs the operation of the command, giving its result."""
        operations = self.project.operations
        metadata = operations.create_metadata(self._get_caller())
        return await operations.run(self._get_operation(), parameters, metadata)

    @abc.abstractmethod
    def _get_operation(
        self,
    ) -> "BoundFactory[BaseOperation[ParametersType, ResultType]]":
        """The operation the command runs: ``self.project.tags.op_list``."""
        raise NotImplementedError(f"{type(self).__qualname__}._get_operation")

    def _get_caller(self) -> "Caller":
        """Who runs the operation: the root, the command line being the operator's."""
        return ROOT_CALLER
