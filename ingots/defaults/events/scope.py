"""The scope of a hold of the events: what it keeps till it ends."""

__all__ = ("EventsScope",)

import typing as t

if t.TYPE_CHECKING:
    from collections.abc import Coroutine


@t.final
class EventsScope:
    """
    A hold of the events published in its block, :meth:`EventsUnit.hold`:
    kept till it ends, then given to the scope it is in, or sent by the
    outermost one. :meth:`discard` drops them, for the one that knows the
    facts they tell are undone: the rollback of a transaction.
    """

    def __init__(self, parent: "EventsScope | None") -> None:
        self._parent = parent
        # the runs of the subscribers, created, not started
        self._pending_coros: "list[Coroutine[t.Any, t.Any, None]]" = []
        self._is_closed = False

    def discard(self) -> None:
        """
        Drops the events held in this scope so far, those the scopes nested
        in it gave it too: their runs closed, never started.
        """
        for coro in self._pending_coros:
            coro.close()
        self._pending_coros.clear()
