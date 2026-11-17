from ingots.testing import ProjectFixture, ProjectTestCase

from . import SEEN, PlayProject


class PlayScenario(ProjectTestCase):
    project = ProjectFixture(PlayProject, configs={"PLAY_NAME": "scenario"})

    async def test_the_game_of_the_run(self) -> None:
        configs = self.project.settings.configs
        SEEN.append(
            {
                "test": "game",
                "host": configs.PLAY_HOST,
                "port": configs.PLAY_PORT,
                "name": configs.PLAY_NAME,
                "is_configure_logging": configs.IS_CONFIGURE_LOGGING,
            }
        )

    async def test_the_second(self) -> None:
        SEEN.append({"test": "second"})


class FailingScenario(ProjectTestCase):
    project = ProjectFixture(PlayProject)

    async def test_fails_when_asked(self) -> None:
        SEEN.append({"test": "failing"})
        self.assertNotEqual(self.project.settings.configs.PLAY_NAME, "fail")
