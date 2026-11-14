# The operations

The fourth unit of the defaults is `operations`: the bricks of the business
logic, called from handlers, commands and views alike, and run with the
permissions of their caller. The unit holds what every operation needs, not
the operations themselves: those live in the units of their domains.

An operation is a {py:class}`~ingots.defaults.operations.BaseOperation`,
typed by its parameters and its result, named `*Operation` (ADR 0014 of the
ecosystem). It declares the permissions a caller needs and runs in the hook
`_run()`:

```python
import typing as t

from ingots.defaults.operations import BaseOperation, PermissionFlags, Permissions
from ingots.puer import Factory, Unit


class Shop(PermissionFlags, domain="shop"):
    PAY = 1 << 0
    REFUND = 1 << 1


class PayOperation(BaseOperation[PayParameters, Receipt]):
    PERMISSIONS = Permissions(Shop.PAY)

    @t.override
    async def _run(self, parameters, metadata):
        ...


class ShopUnit(Unit):
    pay = Factory(PayOperation)
```

The unit of the domain declares it as a {py:class}`~ingots.puer.Factory`,
which creates a new instance for every run, so runs go on concurrently,
each with its own state. A handler, a command or a view only turns the data
of its protocol into the parameters of one operation or more and their
results back; the unit of the operations runs them:

```python
metadata = project.operations.create_metadata(caller, run_uid=request_id)
receipt = await project.operations.run(
    project.shop.pay, PayParameters(amount=5), metadata
)
```

- {py:class}`~ingots.defaults.operations.OperationMetadata` holds the caller
  and the uid of the run. `create_metadata()` takes the id of the request as
  the uid, tying the logs of the client and of the server, or creates a new
  one with `create_run_uid()`, random unless a subclass of the unit decides
  otherwise.
- `operations.run()` hands the operation to `operations.runner`, which a
  subclass of the unit replaces in its slot. The runner binds the uid of the
  run, with the uid of the caller, to the log context: `operation_run_uid`
  and `operation_caller_uid` are in every log record of the run.
- An operation runs another through `operations.run()` too, passing its
  `metadata` on: a chain of operations is one run, under one uid, and each
  operation of it is checked for the caller. An operation running another for someone
  else, the root for one, passes `dataclasses.replace(metadata, caller=...)`.
- `operations.run_safe()` runs an operation whose failure must not fail its
  caller, an entry of an activity log for one: it gives `None` for the
  result instead and, since nothing handles the exception afterwards, logs
  it at `WARNING` with its traceback. A cancellation goes through.
- `operations.checker` lets the caller run the operation: the runner
  creates it, asks what it requires, `get_permissions()`, and gives that to
  the checker; the root runs any, another caller needs every flag of it. A
  refused caller raises `OperationPermissionsError` with the caller, the
  uid of the run and the permissions required; the operation created is
  not run.
- An exception of the operation is raised as it is, so its handler, a
  policy of a server for one, decides by its class; the runner logs it at
  `INFO` without its traceback, by its `repr()`: its message and its
  context, `InsufficientFunds('insufficient funds', 500)`. `started` and `done` are logged at `INFO`,
  with the parameters and the result at `DEBUG`.

A `Caller` is immutable: its `uid`, its `Permissions` and `is_root`.

The callers every project has are those of `operations.callers`, a
{py:class}`~ingots.defaults.operations.CallersProvider`: its attribute
`ROOT` runs any operation, a command of the operator for one; `get_anonymous()` gives the caller of a call that tells no one, a
server's, with what anyone may, nothing by default. An application or an
addon adds to it by the hook `_get_anonymous_permissions()` of a subclass
in the slot, each to what its base gives, so that none takes away what
another gave:

```python
class AppCallers(CallersProvider):
    @t.override
    def _get_anonymous_permissions(self) -> Permissions:
        return super()._get_anonymous_permissions() | Permissions(Shop.PAY)
```

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

## The permissions of an operation

What a caller needs is `get_permissions()` of the operation. By default it
gives the constant `PERMISSIONS`, built once a process and readable from
the class. An operation whose permissions depend on its project overrides
the hook `_get_permissions()` instead, computed on every run, the project
narrowed as everywhere:

```python
class RefundOperation(BaseOperation[RefundParameters, Receipt]):
    project: "ShopProject"

    @t.override
    def _get_permissions(self) -> Permissions:
        if self.project.settings.configs.SHOP_REFUNDS_RESTRICTED:
            return Permissions(Shop.REFUND | Shop.MANAGE)
        return Permissions(Shop.REFUND)
```

A complete operation declares one or the other, `Permissions()` for none:
one that declares neither raises `TypeError` when its class is created. A
base with an abstract method left is not checked, its subclasses are.

## Commands running an operation

A command of the command line that runs an operation extends
{py:class}`~ingots.defaults.operations.BaseOperationCommand`: it gives the
operation in `_get_operation()` and calls `run_operation()` in its `_run()`,
doing what it needs with the result. It runs as the root,
`operations.callers.ROOT`, the command line being the operator's, unless
`_get_caller()` says otherwise:

```python
class PayCommand(BaseOperationCommand[PayParameters, Receipt]):
    cli_name = "pay"

    @t.override
    def _get_operation(self) -> "BoundFactory[PayOperation]":
        return self.project.shop.pay

    @t.override
    async def _run(self) -> None:
        receipt = await self.run_operation(PayParameters(amount=5))
        print(receipt.amount)
```

## Operations run together

Operations independent of each other, taking the same parameters, the
checks of an order for one, run together. A unit declares them in a
{py:class}`~ingots.puer.Factories`, a slot of several classes, in their
order, a class once, typed by what they take:

```python
class ShopUnit(Unit):
    checks = Factories[BaseOperation[Order, t.Any]](StockOperation, LimitOperation)


class AppShopUnit(ShopUnit):
    checks = Factories[BaseOperation[Order, t.Any]](
        *ShopUnit.checks.classes, FraudOperation
    )
```

The type is given, never inferred: mypy then checks that each class takes
what the group gives, and the slot of a subclass against that of its base.
A subclass declares the slot again from the classes of its base, adding,
dropping or replacing some.

```python
results = await project.operations.run_group(project.shop.checks, order, metadata)
reserved = results.get(StockOperation)  # typed by the result of the class
```

- `run_group()` creates the operations and checks the caller for every one
  before any runs: refused one, it raises `OperationPermissionsError` and
  none runs. The context of the logs is bound once for them all.
- They run concurrently, each with the parameters of the group, and every
  one to its end, whatever the others do: their failures come together in
  an `ExceptionGroup`, in the order of their classes. A cancellation goes
  through.
- {py:class}`~ingots.defaults.operations.OperationsResults` gives the result
  of each by the class the group holds; `None` is a result as any other, a
  class the group does not hold raises `KeyError`.

Operations one after the other, the result of one the parameters of the
next, are not a group: one operation runs them.
