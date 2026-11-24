# The events

The fifth unit of the defaults is `events`: a fact of a domain told to its
subscribers after the change that made it, in the background, never
failing it. Three kinds of code meet a change, and only the last is a
subscriber:

| Kind | When | Fails the change | In ingots |
|---|---|---|---|
| a policy | before | yes, a veto | operations run by `run_all_in_group()` |
| a step | in the change, in its transaction | yes | the flow of the operation |
| a reaction | after the fact | no | a subscriber of an event |

A step is a guarantee of the operation, an entry of an activity log for
one, which an application must not switch off by dropping a subscriber;
a reaction, a mail telling the user, is optional, and fails alone.

## An event and its subscribers

An event is a frozen dataclass in the past tense. Its subscribers are
operations taking it, in a {py:class}`~ingots.puer.Factories` of the unit of
its domain, named `ev_<name>`:

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class Paid:
    order_uid: str
    amount: int


class ShopUnit(Unit):
    ev_paid = Factories[BaseOperation[Paid, None]](ReceiptOperation)


class AppShopUnit(ShopUnit):
    ev_paid = Factories[BaseOperation[Paid, None]](
        *ShopUnit.ev_paid.classes, AuditOperation
    )
```

An application adds its subscribers, or drops those of an addon, by
declaring the slot again, as for any group; mypy checks that each takes the
event.

## Publishing

An operation publishes an event after the change it tells is done, the
last thing it does, outside its transaction:

```python
async with storage.transaction():
    ...  # the steps of the change
self.project.events.publish(self.parent.ev_paid, Paid(...), metadata)
```

- `publish()` is not awaited: the subscribers start in the background, by
  {py:meth}`~ingots.defaults.operations.OperationsRunner.run_each_in_group`,
  for the caller of the publisher. One it may not run is skipped, one
  failing is logged; the flow that published never knows.
- A subscriber starts in a context of no hold: what it publishes, it
  publishes on its own.
- The project waits for the subscribers running when it shuts down, before
  its components; `join()` waits for them in a test.

## Holding

`hold()` keeps the events published in its block till it ends, then sends
them, raising or not: a fact published is a fact. A hold in another gives
its events to it, and the outermost sends them; the scope it gives drops
what it holds, `discard()`.

The facade of the transactions of an addon holds the events of a
transaction, and drops them on its rollback, once for all its backends:

```python
async with self.project.events.hold() as held:
    await self.begin()
    try:
        yield
    except BaseException:
        await self.rollback()
        held.discard()
        raise
    await self.commit()
```

An operation run inside the transaction of another publishes as always:
its events go when the outermost transaction commits, and are dropped when
it rolls back. The transactions of several storages are several
transactions: the events follow the outermost hold, and an operation mixing
storages gets no atomicity, of its data nor of its events.
