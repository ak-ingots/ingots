"""
Slots: a parent declares its children as typed descriptors. A
:class:`Slot` holds an entity, a :class:`Factory` creates one on every call;
a :class:`SlotsOwner`, a project or a unit, walks and finds them.
"""

__all__ = ("BaseSlot", "BoundFactory", "Factory", "Slot", "SlotsOwner")

from .base import BaseSlot
from .entity import Slot
from .factory import BoundFactory, Factory
from .owner import SlotsOwner
