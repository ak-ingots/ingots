# The command line

The command line is a domain of the defaults, the unit `cli` of the
project, as `settings` is: its root is a
{py:class}`~ingots.defaults.cli.CliUnit`, its sub-commands are the groups
of its slots, {py:class}`~ingots.defaults.cli.unit.CommandsUnit`s, and the
leaves are the commands, {py:class}`~ingots.defaults.cli.command.BaseCommand`s.
The units of the other domains hold no command: a command reaches the
domain it serves through its project.

```python
import sys

from ingots.defaults import Project
from ingots.defaults.cli import BaseCommand, CliUnit, CommandRunner, CommandsUnit
from ingots.puer import Slot


class MigrateCommand(BaseCommand):
    cli_description = "Applies the pending migrations."
    project: "AppProject"

    async def _run(self) -> None:
        await self.project.storage.migrate()


class StorageCommandsUnit(CommandsUnit):
    cli_description = "Storage management."
    migrate = Slot(MigrateCommand)


class AppCliUnit(CliUnit):
    storage = Slot(StorageCommandsUnit)


class AppProject(Project):
    storage = Slot(StorageUnit)  # the domain, no command in it
    cli = Slot(AppCliUnit)


def main() -> None:
    sys.exit(CommandRunner(AppProject).run())
```

```console
$ app storage migrate
```

## The tree

- The root, `CliUnit`, takes the options of the project, `--config
  NAME=value` and `--configs-file PATH`, read by the loaders of the
  {doc}`settings` from `project.cli.cli_args`, and the commands of the
  defaults: `settings list`, `logging info`, `components list` and
  `components run-forever`.
- An addon extends the root with the group of its own commands, as it
  extends the settings; an application taking several addons joins their
  roots in a class, `AppCliUnit(HttpCliUnit, DbCliUnit)`, a join forgotten
  failing at import time as any other: see {doc}`addon`.
- The tree follows the slots in declaration order, the name of a slot its
  sub-command: `run_forever` is `run-forever`. A slot of a group holds a
  group or a command, else the class fails with a `TypeError`; a group
  without commands is left out.
- Building the command line creates nothing: it walks the classes. Running a
  command creates only the groups on its path: `app storage migrate` creates
  `cli.storage` and `migrate`, nothing else of the tree.
- Every node on the path, the root, the groups, the command, adds its own
  options in `_cli_prepare_parser()` and builds its arguments in
  `_cli_build_args()`; the runner hands them over as `cli_args`, narrowed by an
  annotation (`cli_args: MigrateArgs`).
- {py:class}`~ingots.defaults.cli.parser.CliParser` builds and parses the
  command line, and hands the runner a
  {py:class}`~ingots.defaults.cli.parser.ParsedCommandLine`: the runner's
  arguments, the command's path from the root and the arguments of every
  node on it. A subclass changes how the command line is built through its
  protected hooks (`_get_cli_name()`, `_build_children()`, ...), and a
  runner takes it in `cli_parser_cls`.

## The command runner

{py:class}`~ingots.defaults.cli.runner.CommandRunner` is the
{doc}`runner <../concepts/puer>` whose workflow is one command. It parses the
command line before the run: `sys.argv[1:]`, or the `argv` given to it,
`CommandRunner(AppProject, ["storage", "migrate"]).run()`. Then it runs the
project as every runner does, with the command as the workflow:

- the first stop signal calls `command._stop()`; the graceful timeout is
  `--graceful-timeout SECONDS`;
- `--debug` runs the asyncio event loop in debug mode;
- the exit code is 0 when the command finishes, 1 when a stage fails or is
  cancelled, and 2 for a wrong command line, as usual for `argparse`.
