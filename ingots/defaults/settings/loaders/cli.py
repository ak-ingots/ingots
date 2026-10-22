"""The command line as a source of overrides."""

__all__ = ("CliLoader",)

import typing as t

from .base import BaseLoader, Overrides

if t.TYPE_CHECKING:
    from ingots.defaults.project import Project


class CliLoader(BaseLoader):
    """
    Loads the ``--config NAME=value`` options of the project, the last one
    winning. Loads nothing when the project is not run from the command line.
    """

    project: "Project"

    @t.override
    async def load(self) -> list[Overrides]:
        try:
            args = self.project.cli_args
        except RuntimeError:  # not run from the command line
            return []
        return [Overrides("the command line", dict(args.configs))]
