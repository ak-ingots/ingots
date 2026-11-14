"""
The permissions: bit masks by domain, of a caller or of an operation; the
flags of a unit, bound by its slot ``permissions``, its full name their
domain.
"""

__all__ = (
    "PERMISSION_BITS",
    "BoundPermissions",
    "PermissionFlags",
    "Permissions",
    "PermissionsSlot",
)

import enum
import typing as t
from collections.abc import Mapping

from ingots.puer.slots import BaseSlot

if t.TYPE_CHECKING:
    from collections.abc import Iterator

    from ingots.puer import Entity

PERMISSION_BITS: t.Final = 31
"""The bits of a domain: its mask fits a signed 32-bit integer anywhere."""


class PermissionFlags(enum.IntFlag, boundary=enum.KEEP):
    """
    The flags of a unit, the base of its permissions, nested in it or next
    to it, bound by its slot ``permissions``, :class:`PermissionsSlot`,
    which gives them their domain, the full name of the unit::

        class ShopUnit(OperationsOwner, Unit):
            class Flags(PermissionFlags):
                PAY = 1 << 0
                REFUND = 1 << 1

            permissions = PermissionsSlot(Flags)

    Their masks are stored and sent between services, so a flag keeps its
    bit: it is given explicitly, ``auto()`` raises ``TypeError``, and a bit
    of a flag removed is not given to another. A flag is one bit of its
    own: a group of them is a constant outside, ``Flags.PAY | Flags.REFUND``.
    A mask holding a bit it does not know, of a newer version of the unit,
    keeps it.

    :raises TypeError: a flag is ``auto()``.
    :raises ValueError: a flag is not one of the :data:`PERMISSION_BITS`, or
        is the bit of another flag of the enum.
    """

    @t.override
    @staticmethod
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: list[t.Any]
    ) -> t.Any:
        raise TypeError(f"{name} = auto(): a permission keeps its bit, give it one")

    @t.override
    @classmethod
    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        _check_flags(cls)


class Permissions(Mapping[str, int]):
    """
    The permissions of a caller, or those an operation requires: a bit mask
    per domain. It merges the masks by domain it is given, as a database or
    another service holds them; a flag alone tells no domain, the
    permissions of its unit build its mask::

        Permissions({"shop": 3, "shop.stock": 1})
        project.shop.permissions(ShopUnit.Flags.PAY)  # {"shop": 1}

    Immutable: ``|`` merges two, ``-`` takes the flags of one out of the
    other, :meth:`has` tells whether one covers the other. A domain without
    flags is left out.

    :raises ValueError: a mask is out of :data:`PERMISSION_BITS`.
    """

    __slots__ = ("_masks",)

    def __init__(self, *items: Mapping[str, int]) -> None:
        masks: dict[str, int] = {}
        for item in items:
            for domain, mask in item.items():
                masks[domain] = masks.get(domain, 0) | _check_mask(domain, int(mask))
        self._masks = {domain: mask for domain, mask in masks.items() if mask}

    @t.override
    def __getitem__(self, domain: str) -> int:
        return self._masks[domain]

    @t.override
    def __iter__(self) -> "Iterator[str]":
        return iter(self._masks)

    @t.override
    def __len__(self) -> int:
        return len(self._masks)

    @t.override
    def __hash__(self) -> int:
        return hash(frozenset(self._masks.items()))

    @t.override
    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self._masks!r})"

    def __or__(self, other: Mapping[str, int]) -> "Permissions":
        return Permissions(self, other)

    def __sub__(self, other: Mapping[str, int]) -> "Permissions":
        masks = {domain: mask & ~other.get(domain, 0) for domain, mask in self.items()}
        return Permissions(masks)

    def has(self, required: Mapping[str, int]) -> bool:
        """Whether these permissions have every flag of ``required``."""
        return all(
            self._masks.get(domain, 0) & mask == mask
            for domain, mask in required.items()
        )


class BoundPermissions[FlagsType: PermissionFlags]:
    """
    The permissions of a unit: its :attr:`flags`, the enum, and its
    :attr:`domain`, its full name; called with flags, their mask there::

        permissions = self.parent.permissions
        permissions(permissions.flags.PAY)  # {"shop": 1}
    """

    __slots__ = ("_domain", "_flags")

    def __init__(self, flags: type[FlagsType], domain: str) -> None:
        self._flags = flags
        self._domain = domain

    @property
    def flags(self) -> type[FlagsType]:
        """The flags of the unit, the enum."""
        return self._flags

    @property
    def domain(self) -> str:
        """The domain of the masks, the full name of the unit."""
        return self._domain

    def __call__(self, *flags: FlagsType) -> Permissions:
        """The mask of flags of the unit, in its domain."""
        mask = 0
        for flag in flags:
            mask |= int(flag)
        return Permissions({self._domain: mask})

    @t.override
    def __repr__(self) -> str:
        flags = self._flags.__qualname__
        return f"{type(self).__qualname__}({flags}, {self._domain!r})"


class PermissionsSlot[FlagsType: PermissionFlags](BaseSlot[t.Any]):
    """
    The slot binding the flags of a unit, ``permissions`` of a unit owning
    operations: on the class the slot, :attr:`flags` the enum; on the unit
    its :class:`BoundPermissions`, of the domain of its full name, created
    once a unit, as a factory gives its bound factory. The slot is
    ``permissions`` of every unit, so one enum a unit: a second set of
    flags is of a sub-unit.
    """

    def __init__(self, flags: type[FlagsType]) -> None:
        self._flags = flags

    @property
    def flags(self) -> type[FlagsType]:
        """The flags it binds, the enum."""
        return self._flags

    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...

    @t.overload
    def __get__(self, obj: "Entity", owner: type) -> BoundPermissions[FlagsType]: ...

    @t.final
    def __get__(
        self, obj: "Entity | None", owner: type
    ) -> "t.Self | BoundPermissions[FlagsType]":
        if obj is None:
            return self
        try:
            bound: BoundPermissions[FlagsType] = obj.__dict__[self._key]
        except KeyError:
            bound = obj.__dict__[self._key] = BoundPermissions(
                self._flags, obj.full_name
            )
        return bound

    @t.override
    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self._flags.__qualname__})"


def _check_flags(flags_cls: type[PermissionFlags]) -> None:
    # every flag is one bit of the domain, its own
    names: dict[int, str] = {}
    for name, flag in flags_cls.__members__.items():
        qualname, bit = f"{flags_cls.__qualname__}.{name}", flag.value
        if bit.bit_count() != 1 or bit >= 1 << PERMISSION_BITS:
            raise ValueError(
                f"{qualname}: {bit:#x} is not one of {PERMISSION_BITS} bits"
            )
        if bit in names:
            raise ValueError(f"{qualname}: {bit:#x} is the bit of {names[bit]}")
        names[bit] = name


def _check_mask(name: str, mask: int) -> int:
    if not 0 <= mask < 1 << PERMISSION_BITS:
        raise ValueError(f"{name}: {mask:#x} is out of {PERMISSION_BITS} bits")
    return mask
