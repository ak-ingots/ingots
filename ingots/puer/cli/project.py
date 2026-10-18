"""The project on the command line."""

__all__ = ("CliProject",)

from ingots.puer.project import Project

from .node import CliNode


class CliProject(CliNode, Project):
    """A project driven from the command line: the root parser."""
