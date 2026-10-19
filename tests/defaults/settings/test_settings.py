import contextlib
import io

from ingots.defaults.settings.configs import (
    BoolConfig,
    Configs,
    IntConfig,
    get_config,
    iter_configs,
)
from ingots.puer.cli import CommandRunner

from tests import TestCase

from .settings_fixtures import (
    AppConfigs,
    AppProject,
    DbConfigs,
    HttpConfigs,
    Mode,
)


class ConfigsTestCase(TestCase):
    def test_the_configs_read_their_defaults(self) -> None:
        project = AppProject()
        configs = project.settings.configs
        self.assertIsInstance(configs, AppConfigs)
        self.assertEqual(configs.HTTP_PORT, 8080)
        self.assertEqual(configs.DB_MODE, Mode.SAFE)
        self.assertFalse(configs.IS_PRINT_CONFIGS)

    def test_applying_sets_the_values_of_this_project_only(self) -> None:
        project, other = AppProject(), AppProject()
        project.settings.configs.apply({"HTTP_PORT": 9090})
        self.assertEqual(project.settings.configs.HTTP_PORT, 9090)
        self.assertEqual(project.settings.configs.DB_NAME, "app")
        self.assertEqual(other.settings.configs.HTTP_PORT, 8080)

    def test_the_values_are_applied_once(self) -> None:
        project = AppProject()
        configs = project.settings.configs
        configs.apply({})
        with self.assertRaisesRegex(RuntimeError, "the values are applied"):
            configs.apply({"HTTP_PORT": 9090})
        self.assertEqual(configs.HTTP_PORT, 8080)

    def test_applying_checks_every_value_first(self) -> None:
        project = AppProject()
        configs = project.settings.configs
        with self.assertRaisesRegex(KeyError, "no config 'HTTP_PROT'"):
            configs.apply({"HTTP_PORT": 9090, "HTTP_PROT": 9090})
        with self.assertRaisesRegex(TypeError, "HTTP_PORT: '9090' is not an int"):
            configs.apply({"HTTP_PORT": "9090"})
        self.assertEqual(configs.HTTP_PORT, 8080)
        configs.apply({"HTTP_PORT": 9090})
        self.assertEqual(configs.HTTP_PORT, 9090)

    def test_a_config_cannot_be_assigned(self) -> None:
        project = AppProject()
        configs = project.settings.configs
        with self.assertRaisesRegex(AttributeError, "HTTP_PORT is read-only"):
            configs.HTTP_PORT = 9090  # type: ignore[assignment]

    def test_a_config_is_found_by_name(self) -> None:
        self.assertIs(get_config(AppConfigs, "HTTP_PORT"), HttpConfigs.HTTP_PORT)
        with self.assertRaisesRegex(KeyError, "no config 'apply'"):
            get_config(AppConfigs, "apply")

    def test_the_configs_are_listed_by_name_with_overrides(self) -> None:
        configs = list(iter_configs(AppConfigs))
        self.assertEqual(
            [config.name for config in configs],
            [
                "DB_MODE",
                "DB_NAME",
                "HTTP_BIND",
                "HTTP_PORT",
                "HTTP_TOKEN",
                "IS_PRINT_CONFIGS",
                "IS_STRICT_CONFIGS",
            ],
        )
        self.assertIs(configs[-2], HttpConfigs.IS_PRINT_CONFIGS)
        self.assertIsNot(configs[-2], Configs.IS_PRINT_CONFIGS)


class SettingsTestCase(TestCase):
    def run_project(self, project_cls: type[AppProject], *argv: str) -> str:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(CommandRunner(project_cls, argv).run(), 0)
        return out.getvalue()

    def test_configuring_applies_the_overrides_and_prints_them(self) -> None:
        self.assertEqual(
            self.run_project(
                AppProject,
                *("--config", "IS_PRINT_CONFIGS=on", "--config", "HTTP_PORT=9090"),
                *("--config", "DB_MODE=FAST", "settings", "list"),
            ),
            PRINTED * 2,  # on configuring, then by the command
        )

    def test_the_configs_are_printed_only_when_asked(self) -> None:
        self.assertEqual(
            self.run_project(AppProject, "settings", "list"),
            PRINTED.replace("9090", "8080")
            .replace("FAST", "SAFE")
            .replace("= True", "= False"),
        )


PRINTED = """\
Configs:
DB_MODE = Mode.FAST
DB_NAME = app
HTTP_BIND = ('localhost', 8080)
HTTP_PORT = 9090
HTTP_TOKEN = ***
IS_PRINT_CONFIGS = True
IS_STRICT_CONFIGS = False
------------
"""


class CheckConfigsTestCase(TestCase):
    def test_unrelated_configs_of_one_name_clash(self) -> None:
        class OneConfigs(Configs):
            TIMEOUT = IntConfig(1)

        class OtherConfigs(Configs):
            TIMEOUT = IntConfig(2)

        with self.assertRaisesRegex(
            TypeError,
            r"BothConfigs: \S*OneConfigs.TIMEOUT and \S*OtherConfigs.TIMEOUT are "
            r"different configs: rename one, or declare \S*BothConfigs.TIMEOUT$",
        ):

            class BothConfigs(OneConfigs, OtherConfigs):
                pass

        class ResolvedConfigs(OneConfigs, OtherConfigs):
            TIMEOUT = IntConfig(3)

        class LaterConfigs(ResolvedConfigs, DbConfigs):
            pass

        self.assertEqual(get_config(LaterConfigs, "TIMEOUT").default, 3)

    def test_an_override_of_a_common_ancestor_does_not_clash(self) -> None:
        class QuietConfigs(Configs):
            IS_PRINT_CONFIGS = BoolConfig(False)

        class JoinedConfigs(QuietConfigs, DbConfigs):
            pass

        self.assertIs(
            get_config(JoinedConfigs, "IS_PRINT_CONFIGS"),
            QuietConfigs.IS_PRINT_CONFIGS,
        )

    def test_two_overrides_of_one_config_clash(self) -> None:
        class QuietConfigs(Configs):
            IS_PRINT_CONFIGS = BoolConfig(False)

        class LoudConfigs(Configs):
            IS_PRINT_CONFIGS = BoolConfig(True)

        with self.assertRaisesRegex(TypeError, "QuietConfigs.IS_PRINT_CONFIGS"):

            class JoinedConfigs(QuietConfigs, LoudConfigs):
                pass
