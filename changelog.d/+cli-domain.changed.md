The command line is a domain of the defaults, `ingots.defaults.cli`, the
unit `cli` of the project: its root `CliUnit` takes the options of the
project, `--config` and `--configs-file`, read from `project.cli.cli_args`,
and the commands of the defaults; its sub-commands are groups of commands,
`CommandsUnit`, a slot of one holding a group or a command, else the class
fails. The domains hold no command: `SettingsUnit`, `LoggingUnit` and
`ComponentsUnit` are plain units, their commands in `SettingsCommandsUnit`,
`LoggingCommandsUnit` and `ComponentsCommandsUnit`. An addon extends the
root with the group of its commands, `AuthCliUnit(CliUnit)`, and an
application joins the roots of its addons, as it joins their settings. The
name of a slot is its sub-command: `cli_name` is gone. The command lines
stay as they were. `ingots.testing` gives `TestingCommandsUnit` and
`TestingCliUnit`, `TestingUnit` gone; `ingots.perf` gives
`PerfCommandsUnit`, `PerfCliUnit` and `PerfStandProject`, the base of the
project of a scenario, `PerfUnit` a plain unit.
