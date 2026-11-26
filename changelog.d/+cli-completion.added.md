The completion of the command line by bash: `completion bash` prints its
script, built from the classes, no Python run on Tab; each node completes
its sub-commands and its options, an option its value after a space or an
`=`, by its `choices` or by the hook of its node, `_cli_complete()`, which
gives a `CliCompletion`: the names of the configs after `--config`, the
paths of the components after `--component`, the files after
`--configs-file`. A console script is completed by its name; a script,
`./manage.py`, `python manage.py`, `uv run manage.py`, by its absolute path;
a module, `python -m shop`, `uv run -m shop`, by its name; any other line
by the completion bound to the name before, or loaded for it. A command is
quiet by `cli_is_quiet`: no configs printed on configuring unless asked;
the commands printing for an operator or a shell are. `examples/demo` is an
application of the defaults run by `./manage.py`.
