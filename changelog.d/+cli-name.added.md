A command or a CLI unit names its sub-command with `cli_name`, taken from
its slot when empty; two slots of a unit giving the same sub-command are
refused with a `TypeError`.
