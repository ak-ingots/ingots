"""The components: the unit listing the components of a project."""

__all__ = ("ComponentsUnit",)

from ingots.puer import Component, Unit


class ComponentsUnit(Unit):
    """
    The components of the project, those its slots hold wherever they are;
    the commands ``components list`` and ``components run-forever`` of the
    command line print and run them. The project shuts them down, whatever
    runs them.
    """

    def print_components(self) -> None:
        """Prints every component with its path, class and order."""
        print("Components:")
        for path, slot in self.project.slots_walk(Component):
            print(
                f"{path}: {slot.cls.__qualname__}, "
                f"shutdown order {slot.cls.SHUTDOWN_ORDER}"
            )
        print("-" * 12)
