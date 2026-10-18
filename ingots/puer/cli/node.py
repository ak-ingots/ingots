"""What takes part in the command line."""

__all__ = ("CliNode",)

import typing as t

if t.TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


class CliNode:
    """
    A participant of the command line: a project, a unit, a command or a
    runner. Its class adds its options to its own parser and builds its CLI
    arguments from the parsed namespace; the runner hands them to the
    instance. A subclass narrows their type with an annotation:
    ``cli_args: MyCliArgs``.

    Option destinations share one namespace: prefix them with the node's
    name (``dest="greet_name"``).
    """

    cli_description: t.ClassVar[str] = ""

    @classmethod
    def cli_prepare_parser(cls, parser: "ArgumentParser") -> None:
        """Adds this node's options to its parser. Adds none by default."""

    @classmethod
    def cli_build_args(cls, namespace: "Namespace") -> object:
        """Builds this node's CLI arguments from the namespace. None by default."""
        return None

    @property
    def cli_args(self) -> object:
        """
        The CLI arguments built for this node.

        :raises RuntimeError: the node is not on the path of the command
            being run, so the command line has nothing for it.
        """
        try:
            return self._cli_args
        except AttributeError:
            raise RuntimeError(
                f"{type(self).__qualname__}: no CLI arguments, "
                "it is not on the path of the command being run"
            ) from None

    def _cli_set_args(self, args: object) -> None:
        self._cli_args = args
