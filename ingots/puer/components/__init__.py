"""
Components: entities configured on first use and shut down by the project.
A :class:`Component` is awaited; a :class:`ComponentsOwner`, the project,
configures it once and shuts it down through its
:class:`~ingots.puer.components.lifecycle.ComponentsLifecycle`.
"""

__all__ = ("Component", "ComponentsOwner", "is_configured")

from .component import Component
from .lifecycle import ComponentsOwner, is_configured
