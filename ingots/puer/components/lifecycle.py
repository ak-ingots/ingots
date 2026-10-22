"""The life of the components: configured on first use, shut down by order."""

__all__ = ("ComponentsLifecycle", "ComponentsOwner", "is_configured")

import asyncio
import contextvars
import itertools
import logging
import typing as t

from ingots.puer.constants import ProjectState

from .component import Component

logger = logging.getLogger(__name__)

# the components configuring in this task and in the tasks waiting for it;
# a context variable lives at module level, the components in it are of any
# project
_configuring: contextvars.ContextVar[tuple[Component, ...]] = contextvars.ContextVar(
    "ingots_configuring_components", default=()
)


class ComponentsOwner:
    """
    The owner of the components' life: the project. Every ``await`` of a
    component goes through its :class:`ComponentsLifecycle`.
    """

    @t.final
    def _components_get_lifecycle(self) -> "ComponentsLifecycle":
        """The lifecycle of the owner's components."""
        # created on first use, not in __init__: a subclass whose __init__
        # forgets super() still gets it
        lifecycle: ComponentsLifecycle | None = vars(self).get("_components_lifecycle")
        if lifecycle is None:
            lifecycle = self._components_lifecycle = ComponentsLifecycle()
        return lifecycle


class ComponentsLifecycle:
    """
    The components of one project through their life: configures each once,
    keeps the configured ones and shuts them down by order.
    """

    def __init__(self) -> None:
        # by id(): an entity may compare equal to another, or not hash
        self._configured: dict[int, Component] = {}
        self._configuring: dict[int, asyncio.Task[None]] = {}

    def is_configured(self, component: Component) -> bool:
        """Whether the component is configured and not shut down yet."""
        return id(component) in self._configured

    async def configure[ComponentType: Component](
        self, component: ComponentType
    ) -> ComponentType:
        """
        Configures the component once and gives it back; concurrent callers
        wait for the same configuration, which a cancelled caller does not
        cancel. After a failed configuration, the next call tries again.

        :raises RuntimeError: the project is shutting down, or the component
            waits for itself through the components it configures with.
        """
        chain = _configuring.get()
        if any(item is component for item in chain):
            loop: tuple[Component, ...] = (*chain, component)
            path = " → ".join(map(_describe, loop))
            raise RuntimeError(f"the components wait for each other: {path}")

        task = self._configuring.get(id(component))
        if task is None:
            if self.is_configured(component):
                return component
            state = component.project.state
            if state is not ProjectState.ACTIVE:
                raise RuntimeError(
                    f"{_describe(component)}: the project is {state.value}, "
                    f"no component is configured"
                )
            task = self._configuring[id(component)] = asyncio.create_task(
                self._configure(component, (*chain, component))
            )
        await asyncio.shield(task)
        return component

    async def shut_down(self) -> None:
        """
        Shuts down the configured components, order by order, 1 first; those
        of one order together. A component that fails to shut down is
        logged. A configuration still running is waited for first.
        """
        await asyncio.gather(*self._configuring.values(), return_exceptions=True)
        components = list(self._configured.values())
        self._configured.clear()

        def order(component: Component) -> int:
            return component.SHUTDOWN_ORDER

        for number, group in itertools.groupby(sorted(components, key=order), order):
            batch = list(group)
            logger.debug("shutting down the components of order %s: %s", number, batch)
            results = await asyncio.gather(
                *(item._shut_down() for item in batch), return_exceptions=True
            )
            for component, result in zip(batch, results):
                if isinstance(result, BaseException):
                    logger.error(
                        "%s failed to shut down", _describe(component), exc_info=result
                    )

    async def _configure(
        self, component: Component, chain: tuple[Component, ...]
    ) -> None:
        _configuring.set(chain)
        try:
            await component._configure()  # TODO. should we log the error here?
            self._configured[id(component)] = component
        finally:
            del self._configuring[id(component)]


def is_configured(component: Component) -> bool:
    """Whether the component is configured: awaited, not shut down yet."""
    return component.project._components_get_lifecycle().is_configured(component)


def _describe(component: Component) -> str:
    # the path of the component in its project, found when a message needs it
    try:
        return component.project.slots_find_path(component)
    except LookupError:
        return type(component).__qualname__
