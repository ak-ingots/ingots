"""
Slots: a parent declares its children as typed descriptors. A
:class:`Slot` holds an entity; a :class:`SlotsOwner`, a
project or a unit, walks and finds them.
"""

__all__ = ("Slot", "SlotsOwner")

from .entity import Slot
from .owner import SlotsOwner
