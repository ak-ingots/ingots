import asyncio
import contextlib
import io
import os
import pathlib
import pickle
import tempfile
import typing as t
from unittest import mock

from ingots.defaults import Project, ProjectCliArgs
from ingots.defaults.settings import ConfigsError, Settings
from ingots.defaults.settings.loaders import Overrides
from ingots.puer.cli import CliParser, CommandRunner

from tests import TestCase

from .settings_fixtures import (
    AppProject,
    Mode,
    NoPrefixProject,
    StrictProject,
    VaultProject,
    VerboseCliArgs,
    VerboseProject,
)


class LoaderTestCase(TestCase):
    @t.override
    def setUp(self) -> None:
        self.tmp = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(mock.patch.dict(os.environ, clear=True))

    def write(self, name: str, text: str) -> pathlib.Path:
        path = self.tmp / name
        path.write_text(text)
        return path

    def create_project(
        self, project_cls: type[AppProject] = AppProject, **cli_args: t.Any
    ) -> AppProject:
        project = project_cls()
        project._cli_set_args(ProjectCliArgs(**cli_args))
        return project


class EnvLoaderTestCase(LoaderTestCase):
    def test_the_variables_with_the_prefix_are_loaded(self) -> None:
        os.environ.update(
            {"TEST_HTTP_PORT": "9090", "test_db_name": "shop", "OTHER_PORT": "1"}
        )
        project = AppProject()
        self.assertEqual(
            asyncio.run(project.settings.env_loader.load()),
            [
                Overrides(
                    "the environment (TEST_*)",
                    {"HTTP_PORT": "9090", "DB_NAME": "shop"},
                )
            ],
        )

    def test_a_project_without_a_prefix_fails(self) -> None:
        project = NoPrefixProject()
        with self.assertRaisesRegex(
            RuntimeError, r"^NoPrefixProject.env_configs_prefix is not set$"
        ):
            asyncio.run(project.settings.env_loader.load())


class CliLoaderTestCase(LoaderTestCase):
    def test_the_options_are_loaded_the_last_winning(self) -> None:
        project = self.create_project(
            configs=(("HTTP_PORT", "1"), ("DB_NAME", "x=y"), ("HTTP_PORT", "2"))
        )
        self.assertEqual(
            asyncio.run(project.settings.cli_loader.load()),
            [Overrides("the command line", {"HTTP_PORT": "2", "DB_NAME": "x=y"})],
        )

    def test_nothing_is_loaded_off_the_command_line(self) -> None:
        project = AppProject()
        self.assertEqual(asyncio.run(project.settings.cli_loader.load()), [])
        self.assertEqual(asyncio.run(project.settings.file_loader.load()), [])


class FileLoaderTestCase(LoaderTestCase):
    def load(self, *paths: pathlib.Path) -> list[Overrides]:
        project = self.create_project(configs_files=paths)
        return asyncio.run(project.settings.file_loader.load())

    def test_an_ini_file_gives_the_options_of_every_section(self) -> None:
        path = self.write(
            "app.INI", "HTTP_PORT = 9090\n[db]\nDB_NAME = shop\n[http]\nHTTP_BIND=[]\n"
        )
        [overrides] = self.load(path)
        self.assertEqual(overrides.source, f"the file {str(path)!r}")
        self.assertEqual(
            overrides.data, {"HTTP_PORT": "9090", "DB_NAME": "shop", "HTTP_BIND": "[]"}
        )
        self.assertEqual(overrides.problems, ())

    def test_a_json_file_gives_its_object(self) -> None:
        path = self.write("app.json", '{"HTTP_PORT": 9090, "HTTP_BIND": ["h", 1]}')
        [overrides] = self.load(path)
        self.assertEqual(overrides.data, {"HTTP_PORT": 9090, "HTTP_BIND": ["h", 1]})

    def test_the_files_are_loaded_in_their_order(self) -> None:
        first = self.write("first.json", "{}")
        second = self.write("second.ini", "")
        self.assertEqual(
            [overrides.source for overrides in self.load(second, first)],
            [f"the file {str(second)!r}", f"the file {str(first)!r}"],
        )

    def test_a_file_that_cannot_be_read_is_a_problem(self) -> None:
        cases = {
            "app.yaml": ("HTTP_PORT: 1", "no format for '.yaml'"),
            "broken.json": ("{", "Expecting property name"),
            "list.json": ("[]", "not a JSON object but list"),
            "broken.ini": ("[db", "contains parsing errors"),
        }
        for name, (text, problem) in cases.items():
            with self.subTest(name):
                path = self.write(name, text)
                [overrides] = self.load(path)
                self.assertEqual(overrides.data, {})
                [message] = overrides.problems
                self.assertIn(f"the file {str(path)!r}: ", message)
                self.assertIn(problem, message)
        [overrides] = self.load(self.tmp / "gone.json")
        self.assertIn("No such file", overrides.problems[0])


class ConvertOverridesTestCase(LoaderTestCase):
    def convert(self, *overrides: Overrides) -> dict[str, object]:
        project = AppProject()
        return project.settings.convert_overrides(overrides)

    def test_the_overrides_are_converted_the_later_winning(self) -> None:
        self.assertEqual(
            self.convert(
                Overrides("a", {"HTTP_PORT": "1", "DB_MODE": "FAST"}),
                Overrides("b", {"HTTP_PORT": 2}),
            ),
            {"HTTP_PORT": 2, "DB_MODE": Mode.FAST},
        )

    def test_wrong_overrides_are_logged_and_ignored_by_default(self) -> None:
        with self.assertLogs("ingots.defaults.settings", "WARNING") as logs:
            values = self.convert(
                Overrides("a", {"HTTP_PORT": "x", "HTTP_PROT": "1"}, ("a: broken",)),
                Overrides("b", {"DB_NAME": "shop"}),
            )
        self.assertEqual(values, {"DB_NAME": "shop"})
        self.assertEqual(
            [record.getMessage() for record in logs.records],
            [
                "a: broken; ignored",
                "a: HTTP_PORT: 'x' is not an int; ignored",
                "a: no config HTTP_PROT; ignored",
            ],
        )

    def test_wrong_overrides_fail_in_the_strict_mode(self) -> None:
        with (
            self.assertLogs("ingots.defaults.settings", "ERROR") as logs,
            self.assertRaises(ConfigsError) as raised,
        ):
            self.convert(
                Overrides("a", {"IS_STRICT_CONFIGS": "yes", "HTTP_PORT": "x"}),
                Overrides("b", {"HTTP_PROT": "1"}, ("b: broken",)),
            )
        problems = (
            "b: broken",
            "a: HTTP_PORT: 'x' is not an int",
            "b: no config HTTP_PROT",
        )
        self.assertEqual(raised.exception.problems, problems)
        self.assertEqual(str(raised.exception), "3 wrong overrides of the configs")
        self.assertEqual([record.getMessage() for record in logs.records], [*problems])

    def test_the_error_survives_pickling(self) -> None:
        error = ConfigsError.from_problems(["a: broken"])
        copy = pickle.loads(pickle.dumps(error))
        self.assertEqual(copy.problems, ("a: broken",))
        self.assertEqual(str(copy), "1 wrong override of the configs")

    def test_the_mode_is_read_from_the_overrides_the_later_winning(self) -> None:
        with self.assertLogs("ingots.defaults.settings", "WARNING"):
            values = self.convert(
                Overrides("a", {"IS_STRICT_CONFIGS": "on"}),
                Overrides("b", {"IS_STRICT_CONFIGS": "off", "HTTP_PROT": "1"}),
            )
        self.assertEqual(values, {"IS_STRICT_CONFIGS": False})

    def test_a_mode_that_does_not_convert_is_strict(self) -> None:
        with (
            self.assertLogs("ingots.defaults.settings", "ERROR"),
            self.assertRaises(ConfigsError) as raised,
        ):
            self.convert(Overrides("a", {"IS_STRICT_CONFIGS": "maybe"}))
        self.assertEqual(
            raised.exception.problems, ("a: IS_STRICT_CONFIGS: 'maybe' is not a bool",)
        )

    def test_the_default_mode_is_the_one_of_the_configs(self) -> None:
        project = StrictProject()
        with (
            self.assertLogs("ingots.defaults.settings"),
            self.assertRaises(ConfigsError),
        ):
            project.settings.convert_overrides([Overrides("a", {"HTTP_PROT": "1"})])


class SettingsLoadingTestCase(LoaderTestCase):
    def run_project(self, project_cls: type[Project], *argv: str) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = CommandRunner(project_cls, argv).run()
        return code, err.getvalue()

    def test_the_command_line_wins_over_the_environment_over_files(self) -> None:
        path = self.write(
            "app.json", '{"HTTP_PORT": 1, "DB_NAME": "file", "HTTP_TOKEN": "file"}'
        )
        os.environ.update({"TEST_HTTP_PORT": "2", "TEST_DB_NAME": "env"})
        project = self.create_project(
            configs_files=(path,), configs=(("HTTP_PORT", "3"),)
        )
        asyncio.run(project._configure())
        configs = project.settings.configs
        self.assertEqual(
            (configs.HTTP_PORT, configs.DB_NAME, configs.HTTP_TOKEN), (3, "env", "file")
        )

    def test_the_options_reach_the_loaders(self) -> None:
        path = self.write("app.ini", "HTTP_PORT = 1\nDB_NAME = file\n")
        argv = ("--configs-file", str(path), "--config", "HTTP_PORT=2")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = CommandRunner(AppProject, (*argv, "settings", "list")).run()
        self.assertEqual(code, 0)
        self.assertIn("DB_NAME = file\n", out.getvalue())
        self.assertIn("HTTP_PORT = 2\n", out.getvalue())

    def test_a_loader_of_another_kind_is_added_by_a_slot(self) -> None:
        os.environ["TEST_HTTP_TOKEN"] = "from the environment"
        project = VaultProject()
        asyncio.run(project._configure())
        self.assertEqual(project.settings.configs.HTTP_TOKEN, "from the vault")

    def test_the_loaders_must_be_slots_of_loaders(self) -> None:
        for name in ("configs", "nothing"):
            with (
                self.subTest(name),
                self.assertRaisesRegex(
                    TypeError,
                    rf"BadSettings.LOADERS: {name!r} is not a slot of a loader$",
                ),
            ):

                class BadSettings(Settings):
                    LOADERS = (*Settings.LOADERS, name)

    def test_strict_configuration_fails_the_run(self) -> None:
        os.environ["TEST_IS_STRICT_CONFIGS"] = "1"
        with self.assertLogs(level="ERROR") as logs:
            code, _ = self.run_project(
                AppProject, "--config", "HTTP_PORT=x", "settings", "list"
            )
        self.assertEqual(code, 1)
        self.assertEqual(
            [record.getMessage() for record in logs.records],
            ["the command line: HTTP_PORT: 'x' is not an int", "configuring failed"],
        )
        self.assertIn("1 wrong override of the configs", logs.output[1])

    def test_a_project_adds_options_of_its_own(self) -> None:
        parsed = CliParser(VerboseProject, CommandRunner).parse(
            ["--verbose", "--config", "HTTP_PORT=1", "settings", "list"]
        )
        self.assertEqual(
            parsed.node_args[()],
            VerboseCliArgs(configs=(("HTTP_PORT", "1"),), verbose=True),
        )

    def test_wrong_options_exit_with_2(self) -> None:
        cases = {
            "--config=HTTP_PORT": "'HTTP_PORT' is not NAME=value",
            "--config==1": "'=1' is not NAME=value",
            f"--configs-file={self.tmp}": f"{str(self.tmp)!r} is not a file",
        }
        for option, message in cases.items():
            with self.subTest(option), self.assertRaises(SystemExit) as exit:
                self.run_project(AppProject, option, "settings", "list")
            self.assertEqual(exit.exception.code, 2)
