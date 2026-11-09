`BaseOperationCommand` runs an operation from the command line: a command
gives it in `_get_operation()` and calls `run_operation()`, which gives the
result; the caller is the root unless `_get_caller()` says otherwise.
