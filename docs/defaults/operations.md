# The operations

The fourth unit of the defaults is `operations`: the bricks of the business
logic, called from handlers, commands and views alike, and run with the
permissions of their caller. The unit holds what every operation needs, not
the operations themselves: those live in the units of their domains.

An operation is a {py:class}`~ingots.defaults.operations.BaseOperation`,
typed by its parameters and its result. It declares the permissions a caller
needs and runs in the hook `_run()`:

```python
import typing as t

from ingots.defaults.operations import BaseOperation, PermissionFlags, Permissions
from ingots.puer import Factory, Unit


class Shop(PermissionFlags, domain="shop"):
    PAY = 1 << 0
    REFUND = 1 << 1


class Pay(BaseOperation[PayParameters, Receipt]):
    PERMISSIONS = Permissions(Shop.PAY)

    @t.override
    async def _run(self, parameters, metadata):
        ...


class ShopUnit(Unit):
    pay = Factory(Pay)
```

The unit of the domain declares it as a {py:class}`~ingots.puer.Factory`,
which creates a new instance for every run, so runs go on concurrently,
each with its own state. A handler, a command or a view only turns the data
of its protocol into the parameters of one operation or more and their
results back; the runner of the operations runs them:

```python
metadata = project.operations.create_metadata(caller, run_uid=request_id)
receipt = await project.operations.runner.run(
    project.shop.pay, PayParameters(amount=5), metadata
)
```

- {py:class}`~ingots.defaults.operations.OperationMetadata` holds the caller
  and the uid of the run. `create_metadata()` takes the id of the request as
  the uid, tying the logs of the client and of the server, or creates a new
  one with `create_run_uid()`, random unless a subclass of the unit decides
  otherwise.
- The runner binds the uid of the run, with the uid of the caller, to the
  log context: `operation_run_uid` and `operation_caller_uid` are in every
  log record of the run.
- An operation runs another through the runner too, passing its `metadata`
  on: a chain of operations is one run, under one uid, and each operation of
  it is checked for the caller. An operation running another for someone
  else, the root for one, passes `dataclasses.replace(metadata, caller=...)`.
- `runner.run_safe()` runs an operation whose failure must not fail its
  caller, an entry of an activity log for one: it gives `None` for the
  result instead and, since nothing handles the exception afterwards, logs
  it at `WARNING` with its traceback. A cancellation goes through.
- `operations.checker` lets the caller run the operation, checking its class
  before the factory creates it: the root runs any, another caller needs
  every flag of its `PERMISSIONS`; an operation declares them,
  `Permissions()` for none. A refused caller raises
  `OperationPermissionsError` with the caller, the uid of the run and the
  permissions required.
- An exception of the operation is raised as it is, so its handler, a
  policy of a server for one, decides by its class; the runner logs it at
  `INFO` without its traceback, by its `repr()`: its message and its
  context, `InsufficientFunds('insufficient funds', 500)`. `started` and `done` are logged at `INFO`,
  with the parameters and the result at `DEBUG`.

A `Caller` is immutable: its `uid`, its `Permissions` and `is_root`.
`ROOT_CALLER` runs any operation, `ANONYMOUS_CALLER` holds no permission.
`Permissions` are immutable too, a bit mask per domain: `|` merges two,
`-` takes one out of the other, `has()` tells whether they cover others.
They take the flags of domains and the masks by domain, as a database or
another service holds them: `dict(permissions)` gives
`{"shop": 3, "stock": 1}` back, and `Permissions(data)` takes it.

The flags of a domain are a
{py:class}`~ingots.defaults.operations.PermissionFlags`, naming its
domain. Its masks outlive a run and travel between services, so a flag
keeps its bit across versions:

- A bit is given explicitly; `auto()`, numbering the flags in their order,
  raises `TypeError`. The bit of a flag removed is never given to another;
  a flag renamed keeps it.
- A flag is one bit of its own: two flags of one bit, an alias to `enum`,
  would grant one with the other, and raise `ValueError`. A group of flags
  is a constant outside the class, `SHOP_MANAGE = Shop.PAY | Shop.REFUND`.
- A domain has 31 bits, `PERMISSION_BITS`: its mask fits a signed 32-bit
  integer of any database or protocol. A wider flag or mask raises
  `ValueError`.
- A mask keeps a bit its flags do not know: a service of an older version
  passes on the permissions of a newer one unchanged.

A subclass of the checker in its slot, `checker = Slot(...)`, decides in
`_is_allowed()` otherwise, asking a service for one.
