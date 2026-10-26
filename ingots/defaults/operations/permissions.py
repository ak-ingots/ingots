"""The permissions: bit masks by domain, of a caller or of an operation."""

__all__ = ("PERMISSION_BITS", "PermissionFlags", "Permissions")

import enum
import typing as t
from collections.abc import Mapping

if t.TYPE_CHECKING:
    from collections.abc import Iterator

PERMISSION_BITS: t.Final = 31
"""The bits of a domain: its mask fits a signed 32-bit integer anywhere."""


class PermissionFlags(enum.IntFlag, boundary=enum.KEEP):
    """
    The flags of a domain, the base of its permissions::

        class Shop(PermissionFlags, domain="shop"):
            PAY = 1 << 0
            REFUND = 1 << 1

    Its masks are stored and sent between services, so a flag keeps its
    bit: it is given explicitly, ``auto()`` raises ``TypeError``, and a bit
    of a flag removed is not given to another. A flag is one bit of its
    own: a group of them is a constant outside, ``Shop.PAY | Shop.REFUND``.
    A mask holding a bit it does not know, of a newer version of the
    domain, keeps it.

    :raises TypeError: a flag is ``auto()``.
    :raises ValueError: a flag is not one of the :data:`PERMISSION_BITS`, or
        is the bit of another flag of the domain.
    """

    DOMAIN: t.ClassVar[str]

    @t.override
    @staticmethod
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: list[t.Any]
    ) -> t.Any:
        raise TypeError(f"{name} = auto(): a permission keeps its bit, give it one")

    @t.override
    @classmethod
    def __init_subclass__(cls, *, domain: str, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        _check_flags(cls)
        cls.DOMAIN = domain


class Permissions(Mapping[str, int]):
    """
    The permissions of a caller, or those an operation requires: a bit mask
    per domain. It merges the flags and the masks it is given, the masks
    by domain as a database or another service holds them::

        Permissions(Shop.PAY | Shop.REFUND, Stock.READ)
        Permissions({"shop": 3, "stock": 1})

    Immutable: ``|`` merges two, ``-`` takes the flags of one out of the
    other, :meth:`has` tells whether one covers the other. A domain without
    flags is left out.

    :raises ValueError: a mask is out of :data:`PERMISSION_BITS`.
    """

    __slots__ = ("_masks",)

    def __init__(self, *items: "PermissionFlags | Mapping[str, int]") -> None:
        masks: dict[str, int] = {}
        for item in items:
            pairs = (
                [(item.DOMAIN, int(item))]
                if isinstance(item, PermissionFlags)
                else item.items()
            )
            for domain, mask in pairs:
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
