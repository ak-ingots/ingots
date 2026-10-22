"""
The constants of PUER: enums and values its modules share. It imports
nothing from the package, so every module can import it.
"""

__all__ = ("ProjectState",)

import enum


class ProjectState(enum.Enum):
    """Where a project is in its life; it only moves forward."""

    ACTIVE = "active"
    SHUTTING_DOWN = "shutting down"
    SHUT_DOWN = "shut down"
