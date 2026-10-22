"""The components: the unit running and listing the components of a project."""

__all__ = ("Components",)

from ingots.puer import Component, Slot
from ingots.puer.cli import CliUnit

from .commands import ListComponentsCommand, RunComponentsForeverCommand


class Components(CliUnit):
    """
    The components of the project on the command line: ``components list``
    prints them, ``components run-forever --component PATH`` runs some of
    them, servers typically, until stopped. The project shuts them down,
    whatever runs them.
    """

    cli_description = "The components of the project."
    list = Slot(ListComponentsCommand)
    run_forever = Slot(RunComponentsForeverCommand)

    def print_components(self) -> None:
        """Prints every component with its path, class and order."""
        print("Components:")
        for path, slot in self.project.slots_walk(Component):
            print(
                f"{path}: {slot.cls.__qualname__}, "
                f"shutdown order {slot.cls.SHUTDOWN_ORDER}"
            )
        print("-" * 12)
