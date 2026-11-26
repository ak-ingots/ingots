import pathlib
import subprocess
import sys

from tests import TestCase
from tests.defaults.cli.completion_fixtures import complete

DEMO = pathlib.Path(__file__).parents[2] / "examples" / "demo"


def run_demo(*argv: str) -> str:
    """The standard output of ``python manage.py``, the configs not printed."""
    return subprocess.run(
        [sys.executable, "manage.py", "--config", "IS_PRINT_CONFIGS=off", *argv],
        capture_output=True,
        text=True,
        cwd=DEMO,
        check=True,
    ).stdout


class DemoTestCase(TestCase):
    def test_a_command_of_the_demo(self) -> None:
        self.assertEqual(run_demo("demo", "greet", "--name=Ann"), "Hello, Ann!\n")

    def test_the_completion_of_its_script(self) -> None:
        # the configs printed at the start go to the standard error
        script = subprocess.run(
            [sys.executable, "manage.py", "completion", "bash"],
            capture_output=True,
            text=True,
            cwd=DEMO,
            check=True,
        ).stdout
        scripts = [script]
        self.assertEqual(complete(scripts, "python manage.py de", str(DEMO)), ["demo"])
        self.assertEqual(
            complete(scripts, "python manage.py demo greet --tone=", str(DEMO)),
            ["casual", "formal"],
        )
        self.assertEqual(
            complete(scripts, "python manage.py --config=DEMO_", str(DEMO)),
            ["DEMO_GREETING=", "DEMO_TICK="],
        )
        self.assertEqual(
            complete(
                scripts, "python manage.py components run-forever --component ", "/"
            ),
            [],  # elsewhere manage.py is no script of the demo
        )
        self.assertEqual(
            complete(
                scripts,
                "python manage.py components run-forever --component ",
                str(DEMO),
            ),
            ["greetings.clock"],
        )
