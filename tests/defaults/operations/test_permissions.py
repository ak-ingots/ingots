import dataclasses
import enum
import pickle
import typing as t

from ingots.defaults.operations import (
    PERMISSION_BITS,
    BoundPermissions,
    Caller,
    OperationPermissionsError,
    OperationsOwner,
    PermissionFlags,
    Permissions,
    PermissionsSlot,
)
from ingots.puer import Project, Slot, Unit

from tests import TestCase

from .operations_fixtures import PAY, READ, REFUND, ShopProject, ShopUnit, StockUnit

ANONYMOUS: t.Final = Caller(uid="anonymous")
Shop: t.Final = ShopUnit.Flags


class OutletProject(ShopProject):
    outlet = Slot(StockUnit)  # the stock elsewhere: a domain of its own


class PermissionFlagsTestCase(TestCase):
    def test_the_flags_are_an_enum_of_the_unit(self) -> None:
        self.assertIs(type(Shop.PAY | Shop.REFUND), Shop)
        self.assertEqual(int(Shop.REFUND), 2)

    def test_a_flag_keeps_its_bit(self) -> None:
        with self.assertRaisesRegex(TypeError, "ADD = auto"):

            class Auto(PermissionFlags):
                ADD = enum.auto()

    def test_a_flag_fits_the_bits(self) -> None:
        with self.assertRaisesRegex(
            ValueError, r"Wide\.TOP: 0x80000000 is not one of 31 bits"
        ):

            class Wide(PermissionFlags):
                TOP = 1 << PERMISSION_BITS

    def test_a_flag_is_one_bit_of_its_own_in_the_enum(self) -> None:
        class Refunds(PermissionFlags):
            REFUND = Shop.REFUND.value

        self.assertEqual(int(Refunds.REFUND), int(Shop.REFUND))

        with self.assertRaisesRegex(ValueError, r"Same\.REFUND: 0x1 is the bit of PAY"):

            class Same(PermissionFlags):
                PAY = 1 << 0
                REFUND = 1 << 0

        for mask in (0, 3):
            with self.subTest(mask):
                with self.assertRaisesRegex(
                    ValueError, "Group.BOTH: .* is not one of 31 bits"
                ):

                    class Group(PermissionFlags):
                        PAY = 1 << 0
                        REFUND = 1 << 1
                        BOTH = mask

    def test_a_bit_unknown_to_the_flags_is_kept(self) -> None:
        self.assertEqual(Shop(1 << 5 | Shop.PAY), 33)


class PermissionsSlotTestCase(TestCase):
    def test_the_slot_binds_the_flags_of_its_unit(self) -> None:
        self.assertIs(ShopUnit.permissions.flags, Shop)
        self.assertEqual(repr(ShopUnit.permissions), "PermissionsSlot(ShopUnit.Flags)")
        project = ShopProject()
        permissions = project.shop.permissions
        t.assert_type(permissions, BoundPermissions[ShopUnit.Flags])
        self.assertIs(permissions.flags, Shop)
        self.assertEqual(permissions.domain, "shop")
        self.assertIs(project.shop.permissions, permissions)  # once a unit
        self.assertEqual(repr(permissions), "BoundPermissions(ShopUnit.Flags, 'shop')")

    def test_the_unit_builds_the_masks_of_its_domain(self) -> None:
        project = OutletProject()
        shop, stock, outlet = project.shop, project.shop.stock, project.outlet
        self.assertEqual(shop.permissions(Shop.PAY, Shop.REFUND), PAY | REFUND)
        self.assertEqual(stock.permissions(StockUnit.Flags.READ), READ)
        self.assertEqual(
            outlet.permissions(StockUnit.Flags.READ), Permissions({"outlet": 1})
        )
        self.assertEqual(shop.permissions(), Permissions())

    def test_a_slot_belongs_to_a_unit(self) -> None:
        with self.assertRaisesRegex(TypeError, "slots belong to projects and units"):

            class Loose:
                permissions = PermissionsSlot(Shop)

    def test_a_slot_is_not_assigned(self) -> None:
        class OwnUnit(OperationsOwner, Unit):
            permissions = PermissionsSlot(Shop)

        class OwnProject(Project):
            own = Slot(OwnUnit)

        project = OwnProject()
        with self.assertRaisesRegex(AttributeError, "permissions is a slot"):
            project.own.permissions = None  # type: ignore[assignment]


class PermissionsTestCase(TestCase):
    def test_they_merge_masks_by_domain(self) -> None:
        permissions = Permissions(PAY, {"shop.stock": 1, "empty": 0}, REFUND)
        self.assertEqual(dict(permissions), {"shop": 3, "shop.stock": 1})
        self.assertEqual(permissions["shop"], Shop.PAY | Shop.REFUND)
        self.assertEqual(len(permissions), 2)
        self.assertEqual(repr(permissions), "Permissions({'shop': 3, 'shop.stock': 1})")
        self.assertEqual(Permissions(dict(permissions)), permissions)

    def test_a_mask_fits_the_bits(self) -> None:
        for mask in (-1, 1 << PERMISSION_BITS):
            with self.subTest(mask), self.assertRaisesRegex(ValueError, "shop: "):
                Permissions({"shop": mask})

    def test_they_merge_and_take_out(self) -> None:
        both = PAY | REFUND | {"shop.stock": 1}
        self.assertEqual(both, Permissions({"shop": 3}, READ))
        self.assertEqual(both - REFUND, Permissions(PAY, READ))
        self.assertEqual(both - both, Permissions())
        self.assertEqual(PAY, Permissions({"shop": 1}), "unchanged")

    def test_they_tell_whether_they_cover_others(self) -> None:
        both = PAY | REFUND
        self.assertTrue(both.has(PAY))
        self.assertTrue(both.has(Permissions()))
        self.assertFalse(PAY.has(both))
        self.assertFalse(both.has(READ))

    def test_equal_permissions_hash_alike(self) -> None:
        self.assertEqual(
            hash(Permissions({"shop": 3, "shop.stock": 1})),
            hash(Permissions(READ, PAY | REFUND)),
        )


class CallerTestCase(TestCase):
    def test_a_caller_is_immutable(self) -> None:
        caller = Caller(uid="u1", permissions=PAY)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            caller.uid = "u2"  # type: ignore[misc]
        other = dataclasses.replace(caller, permissions=Permissions())
        self.assertEqual(other, Caller(uid="u1"))


class ErrorTestCase(TestCase):
    def test_the_error_survives_pickling(self) -> None:
        error = OperationPermissionsError.for_caller(ANONYMOUS, "r1", PAY)
        copy = pickle.loads(pickle.dumps(error))
        self.assertEqual(str(copy), "anonymous lacks the permissions of the operation")
        self.assertEqual(copy.caller, ANONYMOUS)
        self.assertEqual(copy.run_uid, "r1")
        self.assertEqual(copy.required, PAY)
