"""
PUER: Project-Unit-Entity-Runner, the core of Ingots.

A project owns units and entities; a unit groups entities; children are
declared as typed slots and customized by subclassing (ADR 0004).
"""

__all__ = (
    "BaseRunner",
    "BoundFactories",
    "BoundFactory",
    "Component",
    "Entity",
    "Factories",
    "Factory",
    "Project",
    "ProjectState",
    "Slot",
    "SlotsOwner",
    "Unit",
    "create_entity",
)

from .components import Component
from .constants import ProjectState
from .entity import Entity, create_entity
from .project import Project
from .runner import BaseRunner
from .slots import BoundFactories, BoundFactory, Factories, Factory, Slot, SlotsOwner
from .unit import Unit
