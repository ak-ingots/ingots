"""The command line parser: built from the slots of the classes, nothing is created."""

__all__ = ("CliParser", "CliTree", "ParsedCommandLine")

import typing as t
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass

from .command import BaseCommand
from .node import CliNode
from .unit import CommandsUnit

if t.TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from ingots.defaults.project import Project


@dataclass(frozen=True, slots=True)
class CliTree:
    """
    A node of the command tree: the unit ``cli`` of the project at the root,
    the groups of commands inside, the commands at the leaves, in the
    declaration order of their slots.
    """

    name: str
    path: tuple[str, ...]
    cls: type[CliNode]
    children: tuple["CliTree", ...] = ()


@dataclass(frozen=True, slots=True)
class ParsedCommandLine:
    """
    What the command line chose: the runner's arguments, the slot path of the
    command from the unit ``cli``, and the arguments of every node on that
    path, by slot path (``()`` for the unit ``cli``).
    """

    runner_args: object
    command_path: tuple[str, ...]
    node_args: "Mapping[tuple[str, ...], object]"


class CliParser:
    """
    Parses the command line of a project class from its unit ``cli``: the
    groups of commands are sub-commands, the commands the leaves, every node
    adds its own options, the runner's go at the root. Nothing is created.

    A subclass changes how the command line is built through the protected
    hooks; a runner takes it in its ``cli_parser_cls``.
    """

    COMMAND_PATH_DEST: t.ClassVar[str] = "_cli_command_path"

    def __init__(self, project_cls: type["Project"], runner_cls: type[CliNode]) -> None:
        self._runner_cls = runner_cls
        root = project_cls.cli.cls
        self._tree = CliTree("", (), root, self._build_children(root, ()))

    @property
    def tree(self) -> CliTree:
        """The command tree."""
        return self._tree

    def parse(self, argv: "Sequence[str] | None") -> ParsedCommandLine:
        """
        Parses ``argv``, ``sys.argv[1:]`` when ``None``. Exits with code 2 on
        a wrong command line, as :mod:`argparse` does.
        """
        namespace = self._build_parser().parse_args(argv)
        path: tuple[str, ...] = getattr(namespace, self.COMMAND_PATH_DEST)
        return ParsedCommandLine(
            runner_args=self._runner_cls._cli_build_args(namespace),
            command_path=path,
            node_args=self._build_node_args(namespace, path),
        )

    def _build_children(
        self, owner_cls: type[CommandsUnit], path: tuple[str, ...]
    ) -> tuple[CliTree, ...]:
        """The tree below a group; a group without commands is left out."""
        children: list[CliTree] = []
        for name, slot in owner_cls.slots_iter():
            child_path = (*path, name)
            grandchildren: tuple[CliTree, ...] = ()
            if issubclass(slot.cls, CommandsUnit):
                grandchildren = self._build_children(slot.cls, child_path)
                if not grandchildren:
                    continue
            cli_name = self._get_cli_name(name)
            children.append(CliTree(cli_name, child_path, slot.cls, grandchildren))
        return tuple(children)

    def _get_cli_name(self, slot_name: str) -> str:
        """The sub-command of a slot: its name with ``-`` for ``_``."""
        return slot_name.replace("_", "-")

    def _get_description(self, cls: type[CliNode]) -> str:
        """The description of a node: its ``cli_description``."""
        return cls.cli_description

    def _build_parser(self) -> ArgumentParser:
        parser = ArgumentParser(description=self._get_description(self._tree.cls))
        self._runner_cls._cli_prepare_parser(parser)
        self._prepare_parser(parser, self._tree)
        return parser

    def _prepare_parser(self, parser: ArgumentParser, tree: CliTree) -> None:
        """Adds the options of a node and the sub-commands below it."""
        tree.cls._cli_prepare_parser(parser)
        if issubclass(tree.cls, BaseCommand):
            parser.set_defaults(**{self.COMMAND_PATH_DEST: tree.path})
        if not tree.children:
            return

        subparsers = parser.add_subparsers(
            title="commands", dest=f"_cli_level_{len(tree.path)}", required=True
        )
        for child in tree.children:
            description = self._get_description(child.cls)
            subparser = subparsers.add_parser(
                child.name,
                help=description.partition("\n")[0],
                description=description,
            )
            self._prepare_parser(subparser, child)

    def _build_node_args(
        self, namespace: Namespace, path: tuple[str, ...]
    ) -> dict[tuple[str, ...], object]:
        node, nodes = self._tree, [self._tree]
        for name in path:
            node = next(child for child in node.children if child.path[-1] == name)
            nodes.append(node)
        return {node.path: node.cls._cli_build_args(namespace) for node in nodes}
