"""
The events: facts of a domain, told to their subscribers after the change
that made them, in the background, never failing it.
"""

__all__ = ("EventsScope", "EventsUnit", "Subscribers")

import asyncio
import contextlib
import contextvars
import typing as t

from ingots.defaults.operations import BaseOperation
from ingots.puer import BoundFactories, Unit

from .scope import EventsScope

if t.TYPE_CHECKING:
    from collections.abc import AsyncIterator, Coroutine

    from ingots.defaults.operations import OperationMetadata
    from ingots.defaults.project import Project

type Subscribers[EventType] = BoundFactories[BaseOperation[EventType, None]]
"""
The subscribers of an event: the slot ``ev_<name>`` of the unit of its
domain, a ``Factories`` of operations taking the event.
"""

# the scope of the hold of the current context: a hold nests in the one the
# context is in; a context variable lives at module level, the scopes in it
# are of any project
_scope: contextvars.ContextVar[EventsScope | None] = contextvars.ContextVar(
    "ingots_events_scope", default=None
)


class EventsUnit(Unit):
    """
    ``project.events``: the one way an event is published, :meth:`publish`.
    Outside a hold, the subscribers of the event start at once, in the
    background; inside one, :meth:`hold`, when the outermost hold ends. A
    subscriber is a reaction to a fact: it runs by
    :meth:`~ingots.defaults.operations.OperationsRunner.run_each_in_group`,
    and fails alone, logged, never the flow that published. Usage::

        class ShopUnit(Unit):
            ev_paid = Factories[BaseOperation[Paid, None]](ReceiptOperation)

        async with storage.transaction():
            ...  # the steps of the change
        project.events.publish(project.shop.ev_paid, Paid(...), metadata)

    The project waits for the subscribers running when it shuts down,
    before its components, :meth:`join`.
    """

    project: "Project"

    def __init__(self) -> None:
        super().__init__()
        self._tasks: set[asyncio.Task[None]] = set()

    @t.final
    def publish[EventType](
        self,
        subscribers: "Subscribers[EventType]",
        event: EventType,
        metadata: "OperationMetadata",
    ) -> None:
        """
        Publishes ``event`` to ``subscribers`` for the caller of ``metadata``,
        not awaited: the flow goes on. Published after the change the event
        tells is done, the last thing of an operation: a fact published is
        a fact.
        """
        coro = self.project.operations.run_each_in_group(subscribers, event, metadata)
        scope = _get_open(_scope.get())
        if scope is None:
            self._schedule_sending(coro)
        else:
            scope._pending_coros.append(coro)

    @t.final
    @contextlib.asynccontextmanager
    async def hold(self) -> "AsyncIterator[EventsScope]":
        """
        Holds the events published in the block till it ends, raising or
        not; the scope it gives drops them, :meth:`EventsScope.discard`. A
        hold in another gives its events to it; the outermost sends them.
        The facade of the transactions of an addon holds the events of a
        transaction, and drops them on its rollback.
        """
        parent = _scope.get()
        scope = EventsScope(parent)
        token = _scope.set(scope)
        try:
            yield scope
        finally:
            _scope.reset(token)
            scope._is_closed = True
            # the hold it is in, if open still: a task may outlive the hold
            # it began in
            outer = _get_open(parent)
            if outer is not None:
                outer._pending_coros.extend(scope._pending_coros)
            else:
                for coro in scope._pending_coros:
                    self._schedule_sending(coro)

    @t.final
    async def join(self) -> None:
        """
        Waits for the subscribers running to end, and for those they publish
        to: for a shutdown, a test.
        """
        # a task done leaves the set by a callback yet to run: awaiting done
        # tasks alone may not yield to it
        while pending := [task for task in self._tasks if not task.done()]:
            await asyncio.gather(*pending, return_exceptions=True)

    @t.final
    def _schedule_sending(self, coro: "Coroutine[t.Any, t.Any, None]") -> None:
        # in a context of no hold: what a subscriber publishes is its own
        context = contextvars.copy_context()
        context.run(_scope.set, None)
        task = asyncio.create_task(coro, context=context)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)


def _get_open(scope: EventsScope | None) -> EventsScope | None:
    # the nearest scope still holding: those of the holds ended are passed by
    while scope is not None and scope._is_closed:
        scope = scope._parent
    return scope
