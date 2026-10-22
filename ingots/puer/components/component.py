"""The component: an entity configured on first use, shut down by the project."""

__all__ = ("Component",)

import typing as t

from ingots.puer.entity import Entity

if t.TYPE_CHECKING:
    from collections.abc import Generator

SHUTDOWN_ORDERS: t.Final = range(1, 10)


class Component(Entity):
    """
    An entity holding a resource: a server, or a client of a server or a
    store. Awaiting it configures it once, through its project, and gives
    it back; the project shuts down the components it configured. Usage::

        redis = await self.project.storage.redis
        await redis.get("key")

    A component configures itself in :meth:`_configure` and releases what
    it holds in :meth:`_shut_down`. How it lives between the two (a client
    reconnecting, a server draining) is its own business.

    :attr:`SHUTDOWN_ORDER`, 1 to 9, orders the shutdown: the components of
    order 1 first, those of one order together.
    """

    SHUTDOWN_ORDER: t.ClassVar[int] = 5

    @t.override
    @classmethod
    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        order = cls.SHUTDOWN_ORDER
        if not (isinstance(order, int) and order in SHUTDOWN_ORDERS):
            raise TypeError(
                f"{cls.__qualname__}.SHUTDOWN_ORDER: {order!r} is not 1 to 9"
            )

    @t.final
    def __await__(self) -> "Generator[t.Any, None, t.Self]":
        lifecycle = self.project._components_get_lifecycle()
        return lifecycle.configure(self).__await__()

    async def _configure(self) -> None:
        """Configures the component: called once, on the first ``await``."""

    async def _shut_down(self) -> None:
        """
        Releases what the component holds: called once, when the project
        shuts down, if it is configured.
        """
