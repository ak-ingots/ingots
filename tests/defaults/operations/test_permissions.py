import dataclasses
import enum
import pickle

from ingots.defaults.operations import (
    ANONYMOUS_CALLER,
    PERMISSION_BITS,
    ROOT_CALLER,
    Caller,
    OperationPermissionsError,
    PermissionFlags,
    Permissions,
)

from tests import TestCase

from .operations_fixtures import Shop, Stock


class PermissionFlagsTestCase(TestCase):
    def test_the_flags_name_their_domain(self) -> None:
        self.assertEqual((Shop.DOMAIN, Stock.DOMAIN), ("shop", "stock"))
        self.assertIs(type(Shop.PAY | Shop.REFUND), Shop)

    def test_a_flag_keeps_its_bit(self) -> None:
        with self.assertRaisesRegex(TypeError, "ADD = auto"):

            class Auto(PermissionFlags, domain="auto"):
                ADD = enum.auto()

    def test_a_flag_fits_the_bits(self) -> None:
        with self.assertRaisesRegex(
            ValueError, r"Wide\.TOP: 0x80000000 is not one of 31 bits"
        ):

            class Wide(PermissionFlags, domain="wide"):
                TOP = 1 << PERMISSION_BITS

    def test_a_flag_is_one_bit_of_its_own_in_the_domain(self) -> None:
        class Refunds(PermissionFlags, domain="refunds"):
            REFUND = Shop.REFUND.value

        self.assertEqual(int(Refunds.REFUND), int(Shop.REFUND))

        with self.assertRaisesRegex(ValueError, r"Same\.REFUND: 0x1 is the bit of PAY"):

            class Same(PermissionFlags, domain="same"):
                PAY = 1 << 0
                REFUND = 1 << 0

        for mask in (0, 3):
            with self.subTest(mask):
                with self.assertRaisesRegex(
                    ValueError, "Group.BOTH: .* is not one of 31 bits"
                ):

                    class Group(PermissionFlags, domain="group"):
                        PAY = 1 << 0
                        REFUND = 1 << 1
                        BOTH = mask

    def test_a_bit_unknown_to_the_flags_is_kept(self) -> None:
        self.assertEqual(Shop(1 << 5 | Shop.PAY), 33)


class PermissionsTestCase(TestCase):
    def test_they_merge_flags_and_masks_by_domain(self) -> None:
        permissions = Permissions(Shop.PAY, {"stock": 1, "empty": 0}, Shop.REFUND)
        self.assertEqual(dict(permissions), {"shop": 3, "stock": 1})
        self.assertEqual(permissions["shop"], Shop.PAY | Shop.REFUND)
        self.assertEqual(len(permissions), 2)
        self.assertEqual(repr(permissions), "Permissions({'shop': 3, 'stock': 1})")
        self.assertEqual(Permissions(dict(permissions)), permissions)

    def test_a_mask_fits_the_bits(self) -> None:
        for mask in (-1, 1 << PERMISSION_BITS):
            with self.subTest(mask), self.assertRaisesRegex(ValueError, "shop: "):
                Permissions({"shop": mask})

    def test_they_merge_and_take_out(self) -> None:
        pay, refund = Permissions(Shop.PAY), Permissions(Shop.REFUND)
        both = pay | refund | {"stock": 1}
        self.assertEqual(both, Permissions(Shop.PAY | Shop.REFUND, Stock.READ))
        self.assertEqual(both - refund, Permissions(Shop.PAY, Stock.READ))
        self.assertEqual(both - both, Permissions())
        self.assertEqual(pay, Permissions(Shop.PAY), "unchanged")

    def test_they_tell_whether_they_cover_others(self) -> None:
        both = Permissions(Shop.PAY | Shop.REFUND)
        self.assertTrue(both.has(Permissions(Shop.PAY)))
        self.assertTrue(both.has(Permissions()))
        self.assertFalse(Permissions(Shop.PAY).has(both))
        self.assertFalse(both.has(Permissions(Stock.READ)))

    def test_equal_permissions_hash_alike(self) -> None:
        self.assertEqual(
            hash(Permissions({"shop": 3, "stock": 1})),
            hash(Permissions(Stock.READ, Shop.PAY | Shop.REFUND)),
        )


class CallerTestCase(TestCase):
    def test_a_caller_is_immutable(self) -> None:
        caller = Caller(uid="u1", permissions=Permissions(Shop.PAY))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            caller.uid = "u2"  # type: ignore[misc]
        other = dataclasses.replace(caller, permissions=Permissions())
        self.assertEqual(other, Caller(uid="u1"))

    def test_the_root_and_the_anonymous(self) -> None:
        self.assertTrue(ROOT_CALLER.is_root)
        self.assertFalse(ANONYMOUS_CALLER.is_root)
        self.assertEqual(ANONYMOUS_CALLER.permissions, Permissions())


class ErrorTestCase(TestCase):
    def test_the_error_survives_pickling(self) -> None:
        required = Permissions(Shop.PAY)
        error = OperationPermissionsError.for_caller(ANONYMOUS_CALLER, "r1", required)
        copy = pickle.loads(pickle.dumps(error))
        self.assertEqual(str(copy), "anonymous lacks the permissions of the operation")
        self.assertEqual(copy.caller, ANONYMOUS_CALLER)
        self.assertEqual(copy.run_uid, "r1")
        self.assertEqual(copy.required, required)
