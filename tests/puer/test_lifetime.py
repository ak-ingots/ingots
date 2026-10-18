import gc
import typing as t
import unittest
import weakref

from ingots.puer import Entity, Slot

from .fixtures import AppProject


class LifetimeTestCase(unittest.TestCase):
    """Entities hold their project weakly: a dropped project dies at once."""

    def assertDiesWhenDropped(self, make: t.Callable[[], AppProject]) -> None:
        gc.disable()
        try:
            p = make()
            ref = weakref.ref(p)
            del p
            self.assertIsNone(ref(), "something keeps the project alive")
        finally:
            gc.enable()
            gc.collect()

    def test_a_used_project_dies_when_dropped(self) -> None:
        def make() -> AppProject:
            p = AppProject()
            p.pkg1_unit.sub_unit.entity.method()
            return p

        self.assertDiesWhenDropped(make)

    def test_a_kept_project_is_caught(self) -> None:
        class Hoarder(Entity):
            def remember(self) -> None:
                self.saved = self.project  # a cycle: project -> hoarder -> project

        class Leaky(AppProject):
            hoarder = Slot(Hoarder)

        def make() -> AppProject:
            p = Leaky()
            p.hoarder.remember()
            return p

        with self.assertRaises(AssertionError):
            self.assertDiesWhenDropped(make)

    def test_an_entity_outliving_its_project_fails_when_it_reaches_for_it(
        self,
    ) -> None:
        p = AppProject()
        entity = p.pkg1_unit.sub_unit.entity
        del p
        gc.collect()
        with self.assertRaisesRegex(ReferenceError, "the project is gone"):
            entity.method()

    def test_a_project_must_be_held(self) -> None:
        # nobody holds the temporary project: it dies after the first dot, and
        # creating the next slot needs it
        with self.assertRaises(ReferenceError):
            AppProject().pkg1_unit.sub_unit
