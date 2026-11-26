`IS_PRINT_CONFIGS` is off by default: `settings list` prints the configs on
demand. Printed on configuring, they go to the standard error, as the logs
do, so that the output of a command is its own; `settings list` prints them
to the standard output.
