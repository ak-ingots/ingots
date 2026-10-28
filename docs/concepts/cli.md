# The command line

A project driven from the command line is a
{py:class}`~ingots.puer.cli.project.CliProject`; its command line is built
from its slots. A {py:class}`~ingots.puer.cli.unit.CliUnit` becomes a
sub-command grouping the commands of its slots, and a
{py:class}`~ingots.puer.cli.command.BaseCommand` is a command:

```python
import sys

from ingots.puer import Slot
from ingots.puer.cli import BaseCommand, CliProject, CliUnit, CommandRunner


class Migrate(BaseCommand):
    cli_description = "Applies the pending migrations."

    async def _run(self) -> None: ...


class Storage(CliUnit):
    cli_description = "Storage management."
    migrate = Slot(Migrate)


class AppProject(CliProject):
    storage = Slot(Storage)


def main() -> None:
    sys.exit(CommandRunner(AppProject).run())
```

```console
$ app storage migrate
```

## The tree

- The tree follows the slots in declaration order; a slot `run_forever` is the
  sub-command `run-forever`. A class names its sub-command with `cli_name`
  instead, so that a unit can tell its commands from its operations by a
  prefix: `cmd_get = Slot(GetCommand)` with `cli_name = "get"` is `get`. Two
  slots of a unit giving the same sub-command are a `TypeError`. A plain
  `Unit` and everything in it stay off the command line, and so does a CLI
  unit without commands.
- Building the command line creates nothing: it walks the classes. Running a
  command creates only the units on its path: `app storage migrate` creates
  `storage` and `migrate`, nothing else.
- Every node on the path (the project, its units, the command) adds its own
  options in `_cli_prepare_parser()` and builds its arguments in
  `_cli_build_args()`; the runner hands them over as `cli_args`, narrowed by an
  annotation (`cli_args: MigrateArgs`).
- {py:class}`~ingots.puer.cli.parser.CliParser` builds and parses the command
  line, and hands the runner a
  {py:class}`~ingots.puer.cli.parser.ParsedCommandLine`: the runner's
  arguments, the command's path and the arguments of every node on it. A
  subclass changes how the command line is built through its protected hooks
  (`_get_cli_name()`, `_build_children()`, ...), and a runner takes it in
  `cli_parser_cls`.

## The command runner

{py:class}`~ingots.puer.cli.runner.CommandRunner` is the
{doc}`runner <puer>` whose workflow is one command. It parses the command
line before the run: `sys.argv[1:]`, or the `argv` given to it,
`CommandRunner(AppProject, ["storage", "migrate"]).run()`. Then it runs the
project as every runner does, with the command as the workflow:

- the first stop signal calls `command._stop()`; the graceful timeout is
  `--graceful-timeout SECONDS`;
- `--debug` runs the asyncio event loop in debug mode;
- the exit code is 0 when the command finishes, 1 when a stage fails or is
  cancelled, and 2 for a wrong command line, as usual for `argparse`.
