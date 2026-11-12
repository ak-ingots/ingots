"""
Slots: a parent declares its children as typed descriptors. A
:class:`Slot` holds an entity, a :class:`Factory` creates one on every call,
:class:`Factories` one of each of its classes; a :class:`SlotsOwner`, a
project or a unit, walks and finds them.
"""

__all__ = (
    "BaseClassesSlot",
    "BaseClassSlot",
    "BaseSlot",
    "BoundFactories",
    "BoundFactory",
    "Factories",
    "Factory",
    "Slot",
    "SlotsOwner",
)

from .base import BaseClassesSlot, BaseClassSlot, BaseSlot
from .entity import Slot
from .factory import BoundFactories, BoundFactory, Factories, Factory
from .owner import SlotsOwner
