import gc
import typing as t
import unittest

from ingots.puer import (
    Entity,
    Factories,
    Factory,
    Project,
    Slot,
    SlotsOwner,
    Unit,
    create_entity,
)

from .fixtures import AppProject, Pkg1SubUnit, Pkg1Unit


class Placed(Entity):
    """Reads its place in its ``__init__``."""

    def __init__(self) -> None:
        super().__init__()
        self.seen = (self.name, self.full_name, self.parent)


class Run(Entity):
    pass


class Audit(Entity):
    pass


class StockUnit(Unit):
    placed = Slot(Placed)
    run = Factory(Run)
    runs = Factories[Entity](Run, Audit)


class ShopUnit(Unit):
    stock = Slot(StockUnit)


class ShopProject(Project):
    shop = Slot(ShopUnit)
    outlet = Slot(StockUnit)


class Labelled(Entity):
    label: str

    def __init__(self) -> None:
        super().__init__()
        self.title = self.label.upper()


class LabelSlot[EntityType: Labelled](Slot[EntityType]):
    """A kind of slot giving its entities a label before their ``__init__``."""

    @t.override
    def _prepare_entity(self, entity: EntityType, parent: SlotsOwner) -> None:
        entity.label = f"#{entity.full_name}"


class LabelledProject(Project):
    tagged = LabelSlot(Labelled)


class PlaceTestCase(unittest.TestCase):
    def test_an_entity_knows_its_parents_and_its_full_name(self) -> None:
        p = AppProject()
        entity = p.pkg1_unit.sub_unit.entity
        self.assertEqual(entity.parents, (p, p.pkg1_unit, p.pkg1_unit.sub_unit))
        self.assertIs(entity.project, p)
        self.assertIs(entity.parent, p.pkg1_unit.sub_unit)
        self.assertEqual(entity.name, "entity")
        self.assertEqual(entity.full_name, "pkg1_unit.sub_unit.entity")
        self.assertEqual(p.pkg1_unit.full_name, "pkg1_unit")
        self.assertEqual(p.pkg1_unit.parents, (p,))

    def test_its_init_has_its_place(self) -> None:
        p = ShopProject()
        stock = p.shop.stock
        self.assertEqual(stock.placed.seen, ("placed", "shop.stock.placed", stock))

    def test_a_unit_placed_twice_has_two_full_names(self) -> None:
        p = ShopProject()
        self.assertEqual(p.shop.stock.full_name, "shop.stock")
        self.assertEqual(p.outlet.full_name, "outlet")
        self.assertEqual(p.outlet.placed.full_name, "outlet.placed")

    def test_the_entities_of_factories_are_at_their_full_name(self) -> None:
        p = ShopProject()
        stock = p.shop.stock
        run = stock.run()
        self.assertEqual((run.full_name, run.parent), ("shop.stock.run", stock))
        self.assertIsNot(stock.run(), run)
        self.assertEqual(
            [(type(entity), entity.full_name) for entity in stock.runs()],
            [(Run, "shop.stock.runs"), (Audit, "shop.stock.runs")],
        )

    def test_the_nearest_parent_of_a_kind_is_found(self) -> None:
        p = AppProject()
        entity = p.pkg1_unit.sub_unit.entity
        t.assert_type(entity.find_parent(Pkg1Unit), Pkg1Unit)
        self.assertIs(entity.find_parent(Pkg1Unit), p.pkg1_unit)
        self.assertIs(entity.find_parent(Unit), p.pkg1_unit.sub_unit)
        self.assertIs(entity.find_parent(Project), p)
        with self.assertRaisesRegex(
            LookupError, "^pkg1_unit.sub_unit.entity: no parent of StockUnit$"
        ):
            entity.find_parent(StockUnit)

    def test_a_kind_of_slot_gives_its_entities_more_before_their_init(
        self,
    ) -> None:
        p = LabelledProject()
        self.assertEqual(p.tagged.title, "#TAGGED")

    def test_an_entity_out_of_the_slots_is_placed_by_hand(self) -> None:
        p = AppProject()
        unit = create_entity(Pkg1SubUnit, p.pkg1_unit)
        self.assertEqual(unit.parents, (p, p.pkg1_unit))
        self.assertEqual(unit.full_name, "pkg1_unit.Pkg1SubUnit")
        named = create_entity(Pkg1SubUnit, p, "spare")
        self.assertEqual((named.full_name, named.parent), ("spare", p))
        self.assertEqual(named.entity.full_name, "spare.entity")

    def test_the_parents_are_held_weakly(self) -> None:
        p = AppProject()
        entity = p.pkg1_unit.sub_unit.entity
        del p
        gc.collect()
        for read in (
            lambda: entity.project,
            lambda: entity.parent,
            lambda: entity.parents,
        ):
            with self.assertRaisesRegex(ReferenceError, "the project is gone"):
                read()

    def test_no_entity_is_created_for_a_project_gone(self) -> None:
        p = AppProject()
        unit = p.pkg1_unit
        del p
        gc.collect()
        with self.assertRaisesRegex(ReferenceError, "^Placed: the project is gone"):
            create_entity(Placed, unit)
