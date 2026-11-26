import os
import pathlib
import sys
import tempfile
import types
import typing as t
from unittest import mock

from ingots.defaults.cli import (
    CliCompletion,
    CompletionKind,
    CompletionTarget,
    RunComponentsForeverCommand,
)

from tests import TestCase

from .completion_fixtures import GameProject, ShopProject, build, complete

ROOT = ["--config", "--configs-file", "--debug", "--graceful-timeout"]


class ConsoleScriptTestCase(TestCase):
    scripts: t.ClassVar[list[str]]

    @t.override
    @classmethod
    def setUpClass(cls) -> None:
        cls.scripts = [build(ShopProject, "--command", "shop")]

    def complete(self, line: str, cwd: str = ".") -> list[str]:
        return complete(self.scripts, line, cwd)

    def test_the_root_its_options_and_sub_commands(self) -> None:
        self.assertEqual(
            self.complete("shop "),
            [*ROOT, "completion", "components", "logging", "settings", "shop"],
        )
        self.assertEqual(self.complete("shop co"), ["completion", "components"])
        self.assertEqual(self.complete("shop --d"), ["--debug"])

    def test_a_node_on_the_path(self) -> None:
        self.assertEqual(self.complete("shop --debug shop "), ["restock"])
        self.assertEqual(self.complete("shop shop restock "), ["--mode"])

    def test_the_choices_of_an_option_after_a_space_or_an_equals(self) -> None:
        for line in ("shop shop restock --mode ", "shop shop restock --mode="):
            with self.subTest(line):
                self.assertEqual(self.complete(line), ["fast", "slow"])
        self.assertEqual(self.complete("shop shop restock --mode=f"), ["fast"])

    def test_the_names_of_the_configs(self) -> None:
        self.assertEqual(self.complete("shop --config SH"), ["SHOP_PORT="])
        self.assertEqual(self.complete("shop --config=SH"), ["SHOP_PORT="])
        self.assertIn("IS_STRICT_CONFIGS=", self.complete("shop --config "))

    def test_a_value_given_is_skipped(self) -> None:
        for line in ("shop --config SHOP_PORT=1 sh", "shop --config=SHOP_PORT=1 sh"):
            with self.subTest(line):
                self.assertEqual(self.complete(line), ["shop"])

    def test_the_paths_of_the_components(self) -> None:
        self.assertEqual(
            self.complete("shop components run-forever --component "),
            ["shop.server"],
        )

    def test_an_option_of_a_subclass_takes_the_default(self) -> None:
        self.assertEqual(
            RunComponentsForeverCommand._cli_complete(ShopProject, "verbose"),
            CliCompletion(),
        )

    def test_the_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pathlib.Path(tmp, "shop.ini").touch()
            for line in ("shop --configs-file sh", "shop --configs-file=sh"):
                with self.subTest(line):
                    self.assertEqual(self.complete(line, tmp), ["shop.ini"])


# the completions of other tools, bound before ours, or loaded by
# bash-completion on demand
DJANGO = "_django() { COMPREPLY=(runserver); }; complete -F _django manage.py"
UV = "_uv() { COMPREPLY=(add); }; complete -F _uv uv"
# what bash-completion leaves on a Tab before ours is sourced
STUB = "_comp_complete_minimal() { COMPREPLY=(a-file); }; " + (
    "complete -F _comp_complete_minimal ./manage.py"
)
LOADER = (
    "_python() { COMPREPLY=(--version); }; "
    "_comp_load() { [[ $2 == python ]] && complete -F _python python; }"
)


class ScriptTestCase(TestCase):
    @t.override
    def setUp(self) -> None:
        tmp = self.enterContext(tempfile.TemporaryDirectory())
        for name in ("shop", "game", "django"):
            pathlib.Path(tmp, name).mkdir()
            pathlib.Path(tmp, name, "manage.py").touch()
        self.shop, self.game = f"{tmp}/shop", f"{tmp}/game"
        self.django = f"{tmp}/django"
        self.scripts = [
            DJANGO,
            UV,
            LOADER,
            build(ShopProject, "--script", f"{self.shop}/manage.py"),
            build(GameProject, "--script", f"{self.game}/manage.py"),
        ]

    def complete(self, line: str, cwd: str) -> list[str]:
        return complete(self.scripts, line, cwd)

    def test_two_projects_each_complete_their_script(self) -> None:
        self.assertEqual(self.complete("python manage.py sh", self.shop), ["shop"])
        self.assertEqual(self.complete("python3 manage.py ga", self.game), ["game"])
        self.assertEqual(self.complete("python manage.py sh", self.game), [])
        self.assertEqual(
            self.complete("python ../shop/manage.py sh", self.game), ["shop"]
        )

    def test_the_options_of_python_before_the_script(self) -> None:
        for line in ("python -X dev manage.py sh", "python -u -O manage.py sh"):
            with self.subTest(line):
                self.assertEqual(self.complete(line, self.shop), ["shop"])

    def test_the_script_run_by_itself(self) -> None:
        self.assertEqual(self.complete("./manage.py sh", self.shop), ["shop"])
        self.assertEqual(self.complete(f"{self.game}/manage.py ga", "/"), ["game"])

    def test_the_stub_of_a_tab_before_is_removed(self) -> None:
        scripts = [STUB, *self.scripts]
        self.assertEqual(complete(scripts, "./manage.py sh", self.shop), ["shop"])

    def test_the_script_run_by_uv(self) -> None:
        for line in (
            "uv run manage.py sh",
            "uv run python manage.py sh",
            "uv run --project . --with=rich python3 manage.py sh",
            "uv run --no-sync manage.py --config=SHOP_PORT=1 sh",
        ):
            with self.subTest(line):
                self.assertEqual(self.complete(line, self.shop), ["shop"])

    def test_another_tool_completes_what_is_not_ours(self) -> None:
        self.assertEqual(self.complete("./manage.py ", self.django), ["runserver"])
        self.assertEqual(self.complete("uv ad", self.shop), ["add"])
        self.assertEqual(self.complete("uv run other.py ", self.shop), ["add"])

    def test_the_completion_bash_completion_loads_for_python(self) -> None:
        self.assertEqual(self.complete("python other.py ", self.shop), ["--version"])
        self.assertEqual(self.complete("python ", self.shop), ["--version"])


class ModuleTestCase(TestCase):
    def test_a_module_by_its_name(self) -> None:
        scripts = [build(ShopProject, "--module", "shop")]
        self.assertEqual(complete(scripts, "python -m shop shop "), ["restock"])
        self.assertEqual(complete(scripts, "uv run -m shop shop "), ["restock"])
        self.assertEqual(complete(scripts, "python -m game "), [])


class TargetTestCase(TestCase):
    def test_the_program_run(self) -> None:
        with mock.patch.object(sys, "argv", ["/usr/bin/shop"]):
            self.assertEqual(
                CompletionTarget.from_argv(),
                CompletionTarget(kind=CompletionKind.COMMAND, name="shop"),
            )
        with mock.patch.object(sys, "argv", ["manage.py"]):
            self.assertEqual(
                CompletionTarget.from_argv(),
                CompletionTarget(
                    kind=CompletionKind.SCRIPT, name=os.path.realpath("manage.py")
                ),
            )
        main = types.ModuleType("__main__")
        main.__spec__ = mock.Mock()
        main.__spec__.name = "shop.__main__"
        with (
            mock.patch.object(sys, "argv", ["/srv/shop/__main__.py"]),
            mock.patch.dict(sys.modules, {"__main__": main}),
        ):
            self.assertEqual(
                CompletionTarget.from_argv(),
                CompletionTarget(kind=CompletionKind.MODULE, name="shop"),
            )

    def test_the_command_takes_the_program_run_by_default(self) -> None:
        with mock.patch.object(sys, "argv", ["/usr/bin/shop"]):
            self.assertIn(
                "complete -F _ingots_command_shop_complete_bound shop",
                build(ShopProject),
            )
