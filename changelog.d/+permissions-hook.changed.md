What a caller needs to run an operation is its `get_permissions()`: the hook
`_get_permissions()` gives the constant `PERMISSIONS` by default, and an
operation whose permissions depend on its project overrides it. The runner
creates the operation, asks it and gives the permissions to the checker:
`PermissionsChecker.check(operation_cls, required, metadata)`. An operation
declaring neither raises `TypeError` when its class is created, not on its
run; a refused caller now costs an instance of the operation, not run.
