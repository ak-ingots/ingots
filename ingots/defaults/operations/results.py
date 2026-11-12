"""The results of the operations run together."""

__all__ = ("OperationsResults",)

import typing as t

if t.TYPE_CHECKING:
    from collections.abc import Mapping

    from .operation import BaseOperation


@t.final
class OperationsResults:
    """
    The results of the operations of a group, by their classes, as
    :meth:`~OperationsRunner.run_group` gives them: :meth:`get` types each
    by the class it is of::

        results = await project.operations.run_group(
            project.shop.checks, order, metadata
        )
        reserved = results.get(StockOperation)  # its result type
    """

    __slots__ = ("_results",)

    def __init__(
        self, results: "Mapping[type[BaseOperation[t.Any, t.Any]], object]"
    ) -> None:
        self._results = dict(results)

    @t.override
    def __repr__(self) -> str:
        names = ", ".join(cls.__qualname__ for cls in self._results)
        return f"{type(self).__qualname__}({names})"

    def get[ResultType](
        self, cls: "type[BaseOperation[t.Any, ResultType]]"
    ) -> ResultType:
        """
        The result of the operation of ``cls``, the class the group holds:
        ``None`` is a result as any other.

        :raises KeyError: the group holds no ``cls``.
        """
        return t.cast(ResultType, self._results[cls])
