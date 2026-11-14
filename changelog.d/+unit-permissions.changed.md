The permissions are of the units owning operations: `PermissionFlags`
takes no `domain=` now, its flags nested in the unit or next to it, bound
by its slot `permissions`, a `PermissionsSlot`, in a unit mixing
`OperationsOwner` in; their domain is the full name of the unit, and a unit
placed twice is of two domains. On the class the slot gives the enum,
`flags`; on a unit a `BoundPermissions`, created once, `flags` and
`domain`, called with flags for their mask. `Permissions` takes masks by
domain only, a flag alone telling no domain. An operation declares no
constant `PERMISSIONS` any more: its hook `_get_permissions()`, abstract,
builds them by the permissions of the unit it reaches, its parent
narrowed, so that mypy checks the flags and the hook, an operation
forgetting it refused where a factory takes it; run anyway, it is refused
to all. An integration adds the permissions of the operations it runs.
