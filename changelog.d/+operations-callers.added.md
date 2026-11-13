The callers every project has, `operations.callers`, a `CallersProvider`:
the root, its attribute `ROOT`, and the anonymous one, `get_anonymous()`,
with what anyone may, nothing by default, which an application or an addon
adds to by the hook `_get_anonymous_permissions()`, each to what its base
gives. A command running an operation runs as `operations.callers.ROOT`.
The module `caller` of the operations is merged into `callers`; the names
stay exported from `ingots.defaults.operations`.
