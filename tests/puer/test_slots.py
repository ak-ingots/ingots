import typing as t
import unittest
from collections.abc import Iterator

from ingots.puer import (
    BoundFactory,
    Component,
    Entity,
    Factory,
    Project,
    Slot,
    Unit,
)
from ingots.puer.slots import BaseSlot

from .components_fixtures import ComponentsProject
from .fixtures import (
    AppCommon,
    AppEntity,
    AppProject,
    AppSubUnit,
    AppUnit,
    Common,
    Pkg1Common,
    Pkg1Entity,
    Pkg1Project,
    Pkg2Project,
)


class SlotOnTheClassTestCase(unittest.TestCase):
    def test_class_access_returns_the_slot(self) -> None:
        slot = AppProject.pkg1_unit
        t.assert_type(slot, Slot[AppUnit])
        self.assertIsInstance(slot, Slot)
        self.assertIs(slot.cls, AppUnit)

    def test_the_slot_class_is_read_only(self) -> None:
        with self.assertRaises(AttributeError):
            AppProject.pkg1_unit.cls = AppUnit  # type: ignore[misc]

    def test_slots_are_listed_in_declaration_order(self) -> None:
        self.assertEqual(
            [(name, slot.cls) for name, slot in AppProject.slots_iter()],
            [
                ("common", AppCommon),
                ("pkg2_unit", Pkg2Project.pkg2_unit.cls),
                ("pkg1_unit", AppUnit),
            ],
        )


class SlotOnTheInstanceTestCase(unittest.TestCase):
    def test_an_entity_is_created_on_first_access_only(self) -> None:
        p = AppProject()
        self.assertEqual(_get_created(p), {})
        unit = p.pkg1_unit
        self.assertEqual(_get_created(p), {"_slot_pkg1_unit": unit})

    def test_an_entity_is_created_once_per_owner(self) -> None:
        p = AppProject()
        self.assertIs(p.pkg1_unit, p.pkg1_unit)
        self.assertIs(p.pkg1_unit.sub_unit.entity, p.pkg1_unit.sub_unit.entity)

    def test_projects_do_not_share_entities(self) -> None:
        a, b = AppProject(), AppProject()
        self.assertIsNot(a.pkg1_unit, b.pkg1_unit)
        self.assertIsNot(a.pkg1_unit.sub_unit.entity, b.pkg1_unit.sub_unit.entity)

    def test_entities_point_to_their_own_project(self) -> None:
        a, b = AppProject(), AppProject()
        self.assertIs(a.pkg1_unit.sub_unit.entity.project, a)
        self.assertIs(b.pkg2_unit.project, b)

    def test_a_slot_cannot_be_assigned(self) -> None:
        p = AppProject()
        with self.assertRaises(AttributeError):
            p.pkg1_unit = p.pkg1_unit  # type: ignore[assignment]


class CustomizationTestCase(unittest.TestCase):
    def test_the_customized_classes_are_used_at_depth(self) -> None:
        p = AppProject()
        t.assert_type(p.pkg1_unit, AppUnit)
        t.assert_type(p.pkg1_unit.sub_unit, AppSubUnit)
        t.assert_type(p.pkg1_unit.sub_unit.entity, AppEntity)
        t.assert_type(p.pkg1_unit.sub_unit.entity.project, AppProject)
        t.assert_type(p.common, AppCommon)
        self.assertIsInstance(p.pkg1_unit.sub_unit.entity, AppEntity)
        self.assertIsInstance(p.common, AppCommon)

    def test_a_customized_entity_extends_the_addon_and_sees_neighbours(self) -> None:
        p = AppProject()
        self.assertEqual(
            p.pkg1_unit.sub_unit.entity.method(), "pkg1(pkg1) + pkg2(pkg2)"
        )

    def test_an_addon_alone_uses_its_own_classes(self) -> None:
        p = Pkg1Project()
        self.assertIs(type(p.common), Pkg1Common)
        self.assertEqual(p.pkg1_unit.sub_unit.entity.method(), "pkg1(pkg1)")


class SlotsCheckTestCase(unittest.TestCase):
    def test_bases_holding_unrelated_classes_need_a_join(self) -> None:
        with self.assertRaisesRegex(
            TypeError, r"Unjoined\.common = Slot\(Pkg1Common\)"
        ):

            class Unjoined(Pkg1Project, Pkg2Project):  # type: ignore[misc]
                pass

    def test_a_slot_cannot_hold_an_unrelated_class(self) -> None:
        class Other(Entity):
            pass

        with self.assertRaisesRegex(TypeError, r"does not extend .*Slot\(Pkg1Common\)"):

            class Unrelated(Pkg1Project):
                common = Slot(Other)  # type: ignore[assignment]

    def test_a_slot_cannot_be_replaced_by_something_else(self) -> None:
        with self.assertRaisesRegex(TypeError, r"Replaced\.common = None"):

            class Replaced(Pkg1Project):
                common = None  # type: ignore[assignment]

    def test_a_slot_can_be_narrowed(self) -> None:
        class Narrowed(Pkg1Common):
            pass

        class App(Pkg1Project):
            common = Slot(Narrowed)

        self.assertIsInstance(App().common, Narrowed)

    def test_only_projects_and_units_own_slots(self) -> None:
        with self.assertRaisesRegex(TypeError, "slots belong to projects and units"):

            class Plain(Entity):
                child = Slot(Common)

    def test_a_project_without_slots_is_fine(self) -> None:
        class Empty(Project):
            pass

        self.assertEqual(list(Empty.slots_iter()), [])


class SlotsOwnerTestCase(unittest.TestCase):
    def test_the_slots_are_iterated_by_kind(self) -> None:
        units = AppProject.slots_iter(Unit)
        t.assert_type(units, Iterator[tuple[str, BaseSlot[Unit]]])
        self.assertEqual(
            [(name, slot.cls) for name, slot in units],
            [("pkg2_unit", Pkg2Project.pkg2_unit.cls), ("pkg1_unit", AppUnit)],
        )
        self.assertEqual(list(AppProject.slots_iter(AppEntity)), [])

    def test_the_slots_are_walked_with_their_paths(self) -> None:
        self.assertEqual(
            [path for path, _ in AppProject.slots_walk()],
            [
                "common",
                "pkg2_unit",
                "pkg1_unit",
                "pkg1_unit.sub_unit",
                "pkg1_unit.sub_unit.entity",
            ],
        )
        self.assertEqual(
            [(path, slot.cls) for path, slot in AppProject.slots_walk(Pkg1Entity)],
            [("pkg1_unit.sub_unit.entity", AppEntity)],
        )

    def test_a_component_kind_gives_the_slots_of_components(self) -> None:
        slots = ComponentsProject.slots_walk(Component)
        t.assert_type(slots, Iterator[tuple[str, BaseSlot[Component]]])
        self.assertEqual(
            [(path, slot.cls.__qualname__) for path, slot in slots],
            [
                ("storage.store", "Store"),
                ("storage.cache", "CachedStore"),
                ("server", "Server"),
            ],
        )
        self.assertEqual(
            [name for name, _ in ComponentsProject.slots_iter(Component)],
            ["server"],
        )

    def test_an_entity_is_found_by_its_path(self) -> None:
        p = AppProject()
        entity = p.slots_find_entity("pkg1_unit.sub_unit.entity", Pkg1Entity)
        t.assert_type(entity, Pkg1Entity)
        self.assertIs(entity, p.pkg1_unit.sub_unit.entity)
        self.assertIs(p.slots_find_entity("common"), p.common)

    def test_the_path_of_an_entity_is_found(self) -> None:
        p = AppProject()
        entity = p.pkg1_unit.sub_unit.entity
        self.assertEqual(p.slots_find_path(entity), "pkg1_unit.sub_unit.entity")
        self.assertEqual(p.slots_find_path(p.pkg1_unit), "pkg1_unit")
        with self.assertRaisesRegex(LookupError, "^no slot of .* holds "):
            p.slots_find_path(AppEntity(p))

    def test_a_wrong_path_creates_nothing(self) -> None:
        p = AppProject()
        for path, kind in [
            ("pkg1_unit.missing", Entity),
            ("pkg1_unit.sub_unit", Pkg1Entity),
            ("", Entity),
        ]:
            with (
                self.subTest(path),
                self.assertRaisesRegex(
                    LookupError, f"^no slot of {kind.__qualname__} at {path!r}$"
                ),
            ):
                p.slots_find_entity(path, kind)
        self.assertEqual(_get_created(p), {})

    def test_the_created_entities_are_walked(self) -> None:
        p = AppProject()
        self.assertEqual(list(p.slots_walk_entities()), [])
        entity = p.pkg1_unit.sub_unit.entity
        self.assertEqual(
            list(p.slots_walk_entities()),
            [p.pkg1_unit, p.pkg1_unit.sub_unit, entity],
        )
        self.assertEqual(
            list(p.slots_walk_entities(Unit)), [p.pkg1_unit, p.pkg1_unit.sub_unit]
        )

    def test_a_forgotten_super_still_checks_and_indexes(self) -> None:
        class Careless(Project):
            common = Slot(Pkg1Common)

            @t.override
            @classmethod
            def __init_subclass__(cls, **kwargs: t.Any) -> None:
                pass  # no super(): SlotsOwner does not see the subclasses

        class Child(Careless):
            pkg1_unit = Slot(AppUnit)

        self.assertNotIn("_slots_index", vars(Child))
        self.assertEqual(
            [name for name, _ in Child.slots_iter()], ["common", "pkg1_unit"]
        )

        class Wrong(Careless):
            common = Slot(Common)  # type: ignore[assignment]

        with self.assertRaisesRegex(TypeError, "Wrong.common = .* does not extend"):
            list(Wrong.slots_iter())


class Run(Entity):
    pass


class LoggedRun(Run):
    pass


class Runs(Unit):
    run = Factory(Run)
    common = Slot(Common)


class RunsProject(Project):
    runs = Slot(Runs)


class FactoryTestCase(unittest.TestCase):
    def test_class_access_returns_the_factory(self) -> None:
        factory = Runs.run
        t.assert_type(factory, Factory[Run])
        self.assertIs(factory.cls, Run)
        self.assertEqual(repr(factory), "Factory(Run)")

    def test_every_call_creates_an_entity_of_the_project(self) -> None:
        p = RunsProject()
        create = p.runs.run
        t.assert_type(create, BoundFactory[Run])
        self.assertIs(create.cls, Run)
        self.assertEqual(repr(create), "BoundFactory(Run)")
        first, second = create(), p.runs.run()
        self.assertIsInstance(first, Run)
        self.assertIsNot(first, second)
        self.assertIs(first.project, p)

    def test_the_owner_keeps_nothing(self) -> None:
        p = RunsProject()
        p.runs.run()
        self.assertEqual(_get_created(p.runs), {})
        self.assertEqual(list(p.slots_walk_entities()), [p.runs])

    def test_a_factory_is_walked_but_holds_no_entity_to_find(self) -> None:
        self.assertEqual(
            [path for path, _ in RunsProject.slots_walk(Run)], ["runs.run"]
        )
        p = RunsProject()
        with self.assertRaisesRegex(LookupError, "no slot of Run at 'runs.run'"):
            p.slots_find_entity("runs.run", Run)
        with self.assertRaises(LookupError):
            p.slots_find_path(p.runs.run())

    def test_a_factory_is_customized_by_a_subclass(self) -> None:
        class AppRuns(Runs):
            run = Factory(LoggedRun)

        p = RunsProject()
        self.assertIsInstance(AppRuns(p).run(), LoggedRun)

    def test_a_factory_and_a_slot_do_not_replace_each_other(self) -> None:
        with self.assertRaisesRegex(TypeError, r"ToSlot\.run = Slot\(Run\)"):

            class ToSlot(Runs):
                run = Slot(Run)  # type: ignore[assignment]

        with self.assertRaisesRegex(TypeError, r"ToFactory\.common = Factory"):

            class ToFactory(Runs):
                common = Factory(Common)  # type: ignore[assignment]

    def test_a_component_or_a_unit_takes_a_slot(self) -> None:
        class Server(Component):
            pass

        for cls in (Server, Runs):
            with self.subTest(cls), self.assertRaisesRegex(TypeError, "has a Slot"):
                Factory(cls)

    def test_a_factory_cannot_be_assigned(self) -> None:
        with self.assertRaises(AttributeError):
            RunsProject().runs.run = Run  # type: ignore[assignment]


def _get_created(owner: object) -> dict[str, object]:
    # the entities kept by the slots, none of the owner's own attributes
    return {key: value for key, value in vars(owner).items() if key[:6] == "_slot_"}
