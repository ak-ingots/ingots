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
  `components run-forever`; and the commands of the command line itself,
  `completion bash`.
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

## The completion by bash

`completion bash` prints the script of the completion of bash for the
program run, built from the classes as the command line is: no Python runs
on Tab. Each node completes its sub-commands and its options, the root
those of the runner too; an option taking a value completes it, after a
space or an `=`: its `choices`, the names of the configs after `--config`,
the paths of the components after `--component`, the files after
`--configs-file`. A value given is skipped.

It needs bash 4.2 or later; bash-completion is not needed, and is
honoured when it is there.

### Installing it

Once, the line of `~/.bashrc` that sources the completions of the scripts,
whatever project they are of:

```bash
for f in ~/.local/share/ingots/completion/*.bash; do [[ -r $f ]] && source "$f"; done
```

Then, a project each, its file, named after the project, in the directory of
the way it is run:

```console
$ mkdir -p ~/.local/share/ingots/completion
$ ./manage.py completion bash > ~/.local/share/ingots/completion/shop.bash
$ python -m shop completion bash > ~/.local/share/ingots/completion/shop.bash
$ mkdir -p ~/.local/share/bash-completion/completions
$ shop completion bash > ~/.local/share/bash-completion/completions/shop
```

A new terminal takes it; the one at hand, by `source` of the file. Then:

```console
$ ./manage.py se<Tab>                    # ./manage.py settings
$ ./manage.py --config=SH<Tab>           # --config=SHOP_PORT=
$ ./manage.py shop restock --mode=<Tab><Tab>   # fast  slow
```

Bash completes a word at once when one fits; when several do, the first Tab
only beeps and the second lists them, `set show-all-if-ambiguous on` of
`~/.inputrc` listing them at the first.

How the program is found:

- A console script, `shop`: bash binds the completion to its name and
  loads its file of `completions/` on the first Tab.
- A script, `./manage.py`, `python manage.py`, `uv run manage.py`, or a
  module, `python -m shop`, `uv run -m shop`: the script binds a function
  to the name of the script, to `python`, `python3` and `uv`, the same in
  every script, which finds the completion of the script of the line by its
  absolute path, from the directory at hand, past the options of python and
  of `uv run`, or of the module by its name. Any other line goes to the
  completion bound to that name before, or that bash-completion loads for
  it, `uv add`, the `manage.py` of Django; then to the files.
- `--command`, `--script` and `--module` name the program instead of the one
  run.

The name of the file is the operator's: what binds a script is its absolute
path, written in the file. Two files of one name overwrite each other, so a
file is named after its project.

### When it does not complete

| What is seen | Why | What to do |
|---|---|---|
| Nothing, in a terminal opened before the file | the file is sourced when a shell starts | a new terminal, or `source` the file |
| The files, for the script of a project moved | the file binds the old path | build the file again |
| Commands of the old version | the file is built from the classes, once | build the file again after an upgrade |
| Nothing for `python manage.py`: `python: command not found` | no `python` on the host, only `python3` | `./manage.py`, `uv run manage.py` or `python3 manage.py` |
| The completion of another project of one console name | bash binds a completion to a name, not to an environment | name their commands apart |
| The options of `python` itself, `-X`, not completed | the function bound to `python` completes the scripts | of no matter for an application; remove the file to have them back |

To see what bash calls for a program, `complete -p ./manage.py manage.py
python uv`: ours start `_ingots_`. Bash looks up the path typed,
`./manage.py`, before its name, `manage.py`: a Tab on it before the file is
sourced leaves there the stub of bash-completion, `_comp_complete_minimal`,
completing the files, which sourcing the file removes; `complete -r
./manage.py` does it by hand.

### Removing it

Remove its file, `rm ~/.local/share/ingots/completion/shop.bash`; the
terminals opened after complete as before. One at hand keeps the completion
until it ends, or `exec bash` starts it again.

### The output of a command for a shell

A command printing for an operator or a shell is quiet,
`cli_is_quiet = True`: the configs are not printed on configuring, unless
the command line turns `IS_PRINT_CONFIGS` on; `settings list`, `logging
info`, `components list`, `completion bash` and `perf plan` are.

### The values of an option

A node completes the value of an option of its own in `_cli_complete()`,
from the classes of the project, a
{py:class}`~ingots.defaults.cli.CliCompletion`:

```python
class RunComponentsForeverCommand(BaseCommand):
    @classmethod
    def _cli_complete(cls, project_cls: type[Project], dest: str) -> CliCompletion:
        if dest == "run_forever_components":
            paths = tuple(path for path, _ in project_cls.slots_walk(Component))
            return CliCompletion(words=paths)
        return super()._cli_complete(project_cls, dest)
```
