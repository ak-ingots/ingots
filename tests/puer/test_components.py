import asyncio
import contextlib
import typing as t
from collections.abc import Iterator

from ingots.puer import Component, Project, ProjectState
from ingots.puer.components import is_configured

from tests import TestCase

from .components_fixtures import (
    EVENTS,
    ComponentsProject,
    FlakyProject,
    FlakyServer,
    LoopProject,
    Store,
)


class ComponentTestCase(TestCase):
    @t.override
    def setUp(self) -> None:
        EVENTS.clear()

    def test_an_awaited_component_is_configured(self) -> None:
        async def use() -> None:
            project = ComponentsProject()
            store = project.storage.store
            t.assert_type(store, Store)
            self.assertFalse(is_configured(store))

            configured = await project.storage.store
            t.assert_type(configured, Store)
            self.assertIs(configured, store)
            self.assertEqual(await store.get("key"), "value")
            self.assertTrue(is_configured(store))

        asyncio.run(use())

    def test_a_component_is_configured_once(self) -> None:
        async def use() -> None:
            project = ComponentsProject()
            await asyncio.gather(project.storage.store, project.storage.store)
            await project.storage.store

        asyncio.run(use())
        self.assertEqual(EVENTS, ["configure Store"])

    def test_a_component_configures_with_others(self) -> None:
        async def use() -> None:
            project = ComponentsProject()
            await project.server

        asyncio.run(use())
        self.assertEqual(EVENTS, ["configure Store", "configure server"])

    def test_a_failed_configuration_is_tried_again(self) -> None:
        async def use() -> None:
            project = FlakyProject()
            with self.assertRaisesRegex(ConnectionError, "the port is taken"):
                await project.server
            self.assertFalse(is_configured(project.server))
            await project.server
            self.assertTrue(is_configured(project.server))

        asyncio.run(use())

    def test_a_cancelled_caller_does_not_cancel_the_configuration(self) -> None:
        async def use() -> None:
            project = ComponentsProject()
            impatient = asyncio.create_task(_await(project.storage.store))
            await asyncio.sleep(0)
            impatient.cancel()
            await project.storage.store
            self.assertTrue(impatient.cancelled())
            self.assertTrue(is_configured(project.storage.store))

        asyncio.run(use())
        self.assertEqual(EVENTS, ["configure Store"])

    def test_components_waiting_for_each_other_fail(self) -> None:
        async def use() -> None:
            project = LoopProject()
            await project.first

        with self.assertRaisesRegex(
            RuntimeError,
            "^the components wait for each other: first → second → first$",
        ):
            asyncio.run(use())

    def test_the_shutdown_order_is_1_to_9(self) -> None:
        with self.assertRaisesRegex(
            TypeError, r"Late.SHUTDOWN_ORDER: 10 is not 1 to 9$"
        ):

            class Late(Component):
                SHUTDOWN_ORDER = 10


class ShutDownTestCase(TestCase):
    @t.override
    def setUp(self) -> None:
        EVENTS.clear()

    def test_the_project_shuts_down_its_components_by_order(self) -> None:
        async def use() -> tuple[Store, ComponentsProject]:
            project = ComponentsProject()
            store = await project.storage.store
            await project.storage.cache
            await project.server
            EVENTS.clear()
            self.assertIs(project.state, ProjectState.ACTIVE)
            await project._do_shut_down()
            return store, project

        store, project = asyncio.run(use())
        self.assertEqual(
            EVENTS, ["shut down server", "shut down CachedStore", "shut down Store"]
        )
        self.assertFalse(is_configured(store))
        self.assertIs(project.state, ProjectState.SHUT_DOWN)

    def test_the_project_releases_its_own_before_the_components(self) -> None:
        class ReleasingProject(ComponentsProject):
            @t.override
            async def _shut_down(self) -> None:
                EVENTS.append("release the project")
                await super()._shut_down()
                raise RuntimeError("boom")

        async def use() -> None:
            project = ReleasingProject()
            await project.storage.store
            with self.assertRaisesRegex(RuntimeError, "boom"):
                await project._do_shut_down()
            self.assertIs(project.state, ProjectState.SHUT_DOWN)

        asyncio.run(use())
        self.assertEqual(
            EVENTS,
            [
                "configure Store",
                "release the project",
                "shut down Store",  # even though it failed
            ],
        )

    def test_only_configured_components_shut_down(self) -> None:
        async def use() -> None:
            project = ComponentsProject()
            project.storage.cache  # created, never awaited
            await project.storage.store
            await project._do_shut_down()
            await project._do_shut_down()  # once only

        asyncio.run(use())
        self.assertEqual(EVENTS, ["configure Store", "shut down Store"])

    def test_a_component_outside_the_slots_shuts_down_too(self) -> None:
        async def use() -> None:
            project = ComponentsProject()
            await Store(project)
            await project._do_shut_down()

        asyncio.run(use())
        self.assertEqual(EVENTS, ["configure Store", "shut down Store"])

    def test_a_failed_shutdown_is_logged(self) -> None:
        async def use() -> FlakyServer:
            project = FlakyProject()
            with contextlib.suppress(ConnectionError):
                await project.server
            server = await project.server
            await project.storage.store
            with self.assertLogs("ingots.puer.components.lifecycle", "ERROR") as logs:
                await project._do_shut_down()
            self.assertEqual(
                [record.getMessage() for record in logs.records],
                ["server failed to shut down: ConnectionError('the socket is gone')"],
            )
            self.assertFalse(is_configured(server))
            return server

        asyncio.run(use())
        self.assertIn("shut down Store", EVENTS)

    def test_no_component_is_configured_after_the_shutdown(self) -> None:
        async def use() -> None:
            project = ComponentsProject()
            await project._do_shut_down()
            with self.assertRaisesRegex(
                RuntimeError, "^storage.store: the project is shut down"
            ):
                await project.storage.store
            with self.assertRaisesRegex(
                RuntimeError, "^Store: the project is shut down"
            ):
                await Store(project)  # named by its class outside the slots

        asyncio.run(use())

    def test_a_running_configuration_is_waited_for(self) -> None:
        async def use() -> None:
            project = ComponentsProject()
            asyncio.ensure_future(_await(project.storage.store))
            await asyncio.sleep(0)
            await project._do_shut_down()

        asyncio.run(use())
        self.assertEqual(EVENTS, ["configure Store", "shut down Store"])

    def test_the_created_components_are_listed(self) -> None:
        project = ComponentsProject()
        project.server
        project.storage.cache
        self.assertEqual(
            list(project.slots_walk_entities()),
            [project.storage, project.storage.cache, project.server],
        )
        components = project.slots_walk_entities(Component)
        t.assert_type(components, Iterator[Component])
        self.assertEqual(list(components), [project.storage.cache, project.server])

    def test_a_project_forgetting_super_still_runs_its_components(self) -> None:
        class CarelessProject(ComponentsProject):
            def __init__(self) -> None:
                pass  # no super().__init__()

        async def use() -> None:
            project = CarelessProject()
            await project.storage.store
            await project._do_shut_down()

        asyncio.run(use())
        self.assertEqual(EVENTS, ["configure Store", "shut down Store"])

    def test_a_plain_project_shuts_down_nothing(self) -> None:
        asyncio.run(Project()._do_shut_down())


async def _await(component: Component) -> None:
    await component
