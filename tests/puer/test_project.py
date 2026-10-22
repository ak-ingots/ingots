import asyncio
import typing as t

from ingots.puer import Project, ProjectState

from tests import TestCase


class ProjectTestCase(TestCase):
    def test_the_shutdown_moves_the_state_forward_once(self) -> None:
        states: list[ProjectState] = []

        class RecordingProject(Project):
            @t.override
            async def _shut_down(self) -> None:
                states.append(self.state)

        async def use() -> RecordingProject:
            project = RecordingProject()
            states.append(project.state)
            await project._do_shut_down()
            await project._do_shut_down()  # once only
            return project

        project = asyncio.run(use())
        self.assertEqual(states, [ProjectState.ACTIVE, ProjectState.SHUTTING_DOWN])
        self.assertIs(project.state, ProjectState.SHUT_DOWN)
