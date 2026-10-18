import gc
import pathlib
import signal
import subprocess
import sys
from unittest import mock

from tests import TestCase

from .runner_fixtures import (
    EVENTS,
    PROJECTS,
    BrokenStopRunner,
    DebugRunner,
    ExitingRunner,
    FailingRunner,
    FailingShutDownProject,
    HangingProject,
    ObstinateRunner,
    RecordingRunner,
    ServingRunner,
    StubbornRunner,
    UnkillableRunner,
)


class RunnerTestCase(TestCase):
    def setUp(self) -> None:
        EVENTS.clear()
        PROJECTS.clear()


class StagesTestCase(RunnerTestCase):
    def test_a_run_configures_works_and_shuts_down(self) -> None:
        self.assertEqual(RecordingRunner().run(), 0)
        self.assertEqual(EVENTS, ["configure", "work, debug=False", "shut down"])

    def test_the_workflow_gives_the_exit_code(self) -> None:
        self.assertEqual(ExitingRunner().run(), 3)

    def test_a_failing_workflow_exits_with_1_and_still_shuts_down(self) -> None:
        with self.assertLogs("ingots.puer.runner", "ERROR") as logs:
            self.assertEqual(FailingRunner().run(), 1)
        self.assertEqual(EVENTS, ["configure", "shut down"])
        self.assertIn("the workflow failed", logs.output[0])

    def test_a_failing_shut_down_exits_with_1(self) -> None:
        with self.assertLogs("ingots.puer.runner", "ERROR") as logs:
            self.assertEqual(RecordingRunner(FailingShutDownProject).run(), 1)
        self.assertIn("shutting down failed", logs.output[0])

    def test_a_failing_shut_down_keeps_the_workflow_exit_code(self) -> None:
        class Runner(ExitingRunner):
            def __init__(self) -> None:
                super().__init__(FailingShutDownProject)

        with self.assertLogs("ingots.puer.runner", "ERROR"):
            self.assertEqual(Runner().run(), 3)

    def test_a_subclass_turns_the_debug_mode_on(self) -> None:
        DebugRunner().run()
        self.assertIn("work, debug=True", EVENTS)


class StoppingTestCase(RunnerTestCase):
    def test_a_signal_asks_the_workflow_to_stop(self) -> None:
        self.assertEqual(ServingRunner().run(), 0)
        self.assertEqual(
            EVENTS, ["configure", "serving", "stop", "served", "shut down"]
        )

    def test_a_workflow_ignoring_stop_is_cancelled_after_the_timeout(self) -> None:
        with self.assertLogs("ingots.puer.runner", "WARNING") as logs:
            self.assertEqual(StubbornRunner().run(), 1)
        self.assertEqual(EVENTS, ["configure", "cancelled", "shut down"])
        self.assertEqual(
            list_messages(logs.output),
            ["the workflow did not stop in time", "the workflow was cancelled"],
        )

    def test_a_failing_stop_still_cancels_after_the_timeout(self) -> None:
        with self.assertLogs("ingots.puer.runner", "WARNING") as logs:
            self.assertEqual(BrokenStopRunner().run(), 1)
        self.assertEqual(
            list_messages(logs.output)[0].splitlines()[0],
            "stopping the workflow failed",
        )
        self.assertEqual(EVENTS, ["configure", "cancelled", "shut down"])

    def test_a_second_signal_cancels_at_once(self) -> None:
        with self.assertLogs("ingots.puer.runner", "WARNING") as logs:
            self.assertEqual(ObstinateRunner().run(), 1)
        self.assertEqual(EVENTS, ["configure", "cancelled", "shut down"])
        self.assertEqual(
            list_messages(logs.output),
            ["SIGTERM received, cancelling", "the workflow was cancelled"],
        )

    def test_a_signal_cancels_configuring_and_then_shutting_down(self) -> None:
        with self.assertLogs("ingots.puer.runner", "WARNING") as logs:
            self.assertEqual(RecordingRunner(HangingProject).run(), 1)
        self.assertEqual(
            EVENTS,
            ["configure", "configure cancelled", "shut down", "shut down cancelled"],
        )
        self.assertEqual(
            list_messages(logs.output),
            [
                "SIGTERM received, cancelling",
                "configuring was cancelled",
                "SIGTERM received, cancelling",
                "shutting down was cancelled",
            ],
        )

    def test_a_third_signal_restores_the_default_action_and_resends(self) -> None:
        # the kill itself is faked here: the next test kills a child process
        with (
            mock.patch("ingots.puer.runner.os") as os_mock,
            self.assertLogs("ingots.puer.runner", "WARNING") as logs,
            self.assertRaises(Killed),
        ):
            os_mock.kill.side_effect = Killed
            UnkillableRunner().run()
        os_mock.kill.assert_called_once_with(
            os_mock.getpid.return_value, signal.SIGTERM
        )
        self.assertEqual(signal.getsignal(signal.SIGTERM), signal.SIG_DFL)
        self.assertIn(
            "SIGTERM received a third time, exiting", list_messages(logs.output)
        )
        # the run is cancelled on the way out, and still shuts down
        self.assertEqual(EVENTS, ["configure", "cancelled", "shut down"])

    def test_a_third_signal_kills_the_process(self) -> None:
        # the process dies by the signal, so it is not this one
        script = (
            "from tests.puer.runner_fixtures import UnkillableRunner\n"
            "UnkillableRunner().run()\n"
        )
        done = subprocess.run(
            [sys.executable, "-c", script],
            cwd=pathlib.Path(__file__).parents[2],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(done.returncode, -signal.SIGTERM, done.stderr)
        self.assertIn("SIGTERM received a third time, exiting", done.stderr)

    def test_the_signal_handlers_are_removed_after_the_run(self) -> None:
        RecordingRunner().run()
        self.assertIs(signal.getsignal(signal.SIGINT), signal.default_int_handler)
        self.assertEqual(signal.getsignal(signal.SIGTERM), signal.SIG_DFL)


class LifetimeTestCase(RunnerTestCase):
    def test_the_runner_drops_the_project_when_done(self) -> None:
        gc.disable()
        try:
            runner = RecordingRunner()
            runner.run()
            (ref,) = PROJECTS
            self.assertIsNone(ref(), "something keeps the project alive")
        finally:
            gc.enable()

    def test_no_project_is_running_outside_a_run(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "no project is running"):
            RecordingRunner().project


def list_messages(output: list[str]) -> list[str]:
    # "LEVEL:logger:message" -> "message"
    return [line.split(":", 2)[2] for line in output]


class Killed(SystemExit):
    """Stands for the process killed by a signal: it ends the event loop."""
