import asyncio
import configparser
import contextlib
import csv
import io
import json
import math
import os
import pathlib
import shutil
import sys
import tempfile
import time
import typing as t
from unittest import mock

from ingots.defaults import Project
from ingots.perf import (
    Call,
    CsvSeed,
    LoadGroup,
    PerfUnit,
    Recorder,
    ReportRow,
    ScenarioModuleError,
    SmokeFailedError,
    find_configs_files,
    load_scenario,
    run_scenario,
)
from ingots.perf import points
from ingots.perf.__main__ import main
from ingots.perf.commands import run_clients
from ingots.perf.points import PointPart, measure_actions, read_cgroups
from ingots.puer import Slot

from tests import TestCase

from .fixtures import STAND, ScenariosProject

SCENARIOS = STAND / "scenarios"
PERF_INI = STAND / "perf.ini"


class PerfTestCase(TestCase):
    """A scenario run by its command, in a directory of its own."""

    @t.override
    def setUp(self) -> None:
        self.enterContext(mock.patch.dict(os.environ, clear=False))
        for name in [n for n in os.environ if n.startswith("PERF_TEST_")]:
            del os.environ[name]
        self.work = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))

    def run_perf(
        self,
        scenario: str,
        *command: str,
        files: tuple[pathlib.Path, ...] = (),
        **configs: str,
    ) -> tuple[int, str, str]:
        """``perf <command>`` of a scenario of the stand: its exit code, its output."""
        argv = [
            *(arg for path in files for arg in ("--configs-file", str(path))),
            *("--config", "IS_CONFIGURE_LOGGING=off"),
            *("--config", "IS_PRINT_CONFIGS=off"),
            *("--config", f"PERF_WORK={self.work}"),
            *("--config", f"PERF_REPORTS={self.work / 'reports'}"),
            *(arg for item in configs.items() for arg in ("--config", "=".join(item))),
            "perf",
            *command,
        ]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run_scenario(SCENARIOS / f"{scenario}.py", argv)
        return code, out.getvalue(), err.getvalue()

    def read_report(self, scenario: str, run: str) -> list[dict[str, str]]:
        path = self.work / "reports" / scenario / f"{run}.csv"
        with path.open(newline="") as file:
            return list(csv.DictReader(file))


class LoadScenarioTestCase(PerfTestCase):
    def test_the_project_of_the_module(self) -> None:
        project_cls = load_scenario(SCENARIOS / "echo.py")
        self.assertEqual(project_cls.__name__, "PerfProject")
        self.assertTrue(issubclass(project_cls, ScenariosProject))

    def test_a_name_with_dashes(self) -> None:
        path = self.work / "get-own-profile.py"
        path.write_text((SCENARIOS / "echo.py").read_text())
        project: t.Any = load_scenario(path)()
        self.assertEqual(project.perf._get_scenario(), "get-own-profile")

    def test_a_module_a_run_cannot_take(self) -> None:
        cases = {
            "nothing.py": ("x = 1\n", "no PerfProject, a PerfStandProject"),
            "number.py": ("PerfProject = 1\n", "no PerfProject, a PerfStandProject"),
            "plain.py": (
                "from ingots.defaults import Project\n"
                "class PerfProject(Project):\n    pass\n",
                "no PerfProject, a PerfStandProject",
            ),
            "bare.py": (
                "from ingots.perf import PerfStandProject\n"
                "class PerfProject(PerfStandProject):\n    pass\n",
                "PerfProject gives no PerfUnit of its own in its slot perf",
            ),
        }
        for name, (text, reason) in cases.items():
            with self.subTest(name):
                path = self.work / name
                path.write_text(text)
                with self.assertRaises(ScenarioModuleError) as caught:
                    load_scenario(path)
                self.assertEqual(str(caught.exception), f"{path}: {reason}")
                self.assertEqual(caught.exception.path, str(path))
        with self.assertRaisesRegex(ScenarioModuleError, "no such module"):
            load_scenario(self.work / "missing.py")


class PlanTestCase(PerfTestCase):
    def test_the_configs_resolved_for_the_shell(self) -> None:
        code, out, _ = self.run_perf(
            "duel",
            "plan",
            PERF_ROUNDS="5",
            PERF_HOST_STATE="boost 0; ide off",
        )
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertIn("PERF_GROUPS=2", lines)  # the scenario's file over the stand's
        self.assertIn("PERF_ROUNDS=5", lines)  # the command line over both
        self.assertIn("PERF_WARMUP=0.05", lines)  # the stand's
        self.assertIn("PERF_HOST_STATE='boost 0; ide off'", lines)
        self.assertIn("PERF_CGROUPS=''", lines)
        self.assertTrue(all(line.startswith("PERF_") for line in lines), lines)

    def test_a_file_given_over_those_found(self) -> None:
        given = self.work / "given.ini"
        given.write_text("PERF_GROUPS = [7]\nPERF_ROUNDS = 4\n")
        code, out, _ = self.run_perf("duel", "plan", files=(given,))
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertIn("PERF_GROUPS=7", lines)  # given wins over the found
        self.assertIn("PERF_ROUNDS=4", lines)
        self.assertEqual(
            find_configs_files(SCENARIOS / "duel.py"),
            (PERF_INI, SCENARIOS / "duel.ini"),
        )
        self.assertEqual(find_configs_files(self.work / "alone.py"), ())


class SeedTestCase(PerfTestCase):
    def test_the_rows_of_the_largest_point_typed_back(self) -> None:
        # a copy of the stand: its relative paths, its default work, are of it
        stand = pathlib.Path(shutil.copytree(STAND, self.work / "stand"))
        duel = stand / "scenarios/duel.py"
        argv = [
            "--config",
            "IS_CONFIGURE_LOGGING=off",
            "--config",
            "IS_PRINT_CONFIGS=off",
        ]
        argv += ["--config", "PERF_GROUPS=[1, 3]", "perf", "seed"]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_scenario(duel, argv), 0)
        with (stand / "work/seed.csv").open(newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 3)
        self.assertEqual(list(rows[0]), ["inviter", "invitee", "rank", "is_ranked"])
        project: t.Any = load_scenario(duel)()
        pairs = project.perf.seed.read()
        self.assertEqual(
            [(p.rank, p.is_ranked) for p in pairs], [(0, True), (1, False), (2, True)]
        )

    def test_a_scenario_seeding_nothing_has_no_file(self) -> None:
        stale = self.work / "seed.csv"
        stale.write_text("stale\n")
        code, _, _ = self.run_perf("echo", "seed")
        self.assertEqual(code, 0)
        self.assertFalse(stale.exists())


class PointTestCase(PerfTestCase):
    def test_the_rows_of_a_point_and_its_run(self) -> None:
        cgroup = self.work / "cgroup"
        cgroup.mkdir()
        (cgroup / "cpu.stat").write_text("usage_usec 2000000\nuser_usec 1\n")
        code, _, err = self.run_perf(
            "echo",
            "point",
            "--groups",
            "3",
            PERF_RUN="r1",
            PERF_ROLE="baseline",
            PERF_REF="v1.0.0",
            PERF_CGROUPS=json.dumps([f"app={cgroup}"]),
        )
        self.assertEqual(code, 0, err)
        rows = self.read_report("echo", "r1")
        metrics = {(r["action"], r["metric"]): r["value"] for r in rows}
        self.assertGreater(int(metrics["echo", "calls"]), 0)
        self.assertEqual(metrics["echo", "void"], "")
        for metric in ("rps", "p50_ms", "p95_ms", "p99_ms"):
            self.assertIn(("echo", metric), metrics)
        self.assertEqual(metrics["point", "cpu_cores_app"], "0.0")
        self.assertEqual(metrics["point", "cpu_ms_per_call"], "0.0")
        self.assertIn(("point", "load_cpu"), metrics)
        self.assertEqual(
            {(r["role"], r["round"], r["groups"]) for r in rows},
            {("baseline", "1", "3")},
        )
        run = configparser.ConfigParser(interpolation=None)
        run.optionxform = str  # type: ignore[assignment,method-assign]
        run.read(self.work / "reports/echo/r1.ini")
        self.assertEqual(run["run"]["PERF_GROUPS"], "1 3")
        self.assertNotIn("PERF_ROLE", run["run"])
        self.assertEqual(run["role baseline"]["PERF_REF"], "v1.0.0")
        self.assertIn("python", run["host"])

    def test_the_time_between_two_clients_of_a_group(self) -> None:
        self.assertEqual(self.run_perf("duel", "seed")[0], 0)
        code, _, err = self.run_perf("duel", "point", "--groups", "2", PERF_RUN="r2")
        self.assertEqual(code, 0, err)
        actions = {row["action"] for row in self.read_report("duel", "r2")}
        self.assertEqual(actions, {"invite", "invited-to-accepted", "point"})

    def test_a_process_failing_fails_the_point(self) -> None:
        code, _, err = self.run_perf(
            "failing", "point", "--groups", "1", FAILING_IS_BROKEN="on"
        )
        self.assertEqual(code, 1)
        self.assertIn("a process of the load failed", err)

    def test_a_process_failing_before_it_is_ready(self) -> None:
        (self.work / "seed.csv").write_text("nobody\nx\n")
        code, _, err = self.run_perf("duel", "point", "--groups", "1")
        self.assertEqual(code, 1)
        self.assertIn("ended before it was ready", err)


class LoadTestCase(PerfTestCase):
    """A process of the load in the process of the test, as a point runs it."""

    def test_its_groups_measured_in_the_window(self) -> None:
        out = self.work / "part.json"
        stdin = io.StringIO(f"{time.time()}\n")
        with mock.patch.object(sys, "stdin", stdin):
            code, told, err = self.run_perf(
                "echo",
                "load",
                *("--groups", "2", "--part", "0", "--parts", "1"),
                *("--out", str(out)),
            )
        self.assertEqual(code, 0, err)
        self.assertIn("ready", told)
        part = PointPart.load(out.read_text())
        self.assertTrue(part.calls and all(c.action == "echo" for c in part.calls))
        self.assertGreater(part.cpu, 0.0)  # the clients worked in the window


class SmokeTestCase(PerfTestCase):
    def test_a_group_once_into_the_dry_report(self) -> None:
        code, _, err = self.run_perf("duel", "smoke", PERF_RUN="d1")
        self.assertEqual(code, 0, err)
        rows = self.read_report("dry/duel", "d1")
        self.assertEqual({r["action"] for r in rows}, {"invite", "invited-to-accepted"})
        self.assertEqual({r["role"] for r in rows}, {"dry"})

    def test_an_action_erring_fails_it(self) -> None:
        with self.assertLogs("ingots", "ERROR") as logs:
            code, _, _ = self.run_perf("failing", "smoke")
        self.assertEqual(code, 1)
        self.assertIn("failing: fail: LookupError", "\n".join(logs.output))

    def test_no_action_measured_fails_it(self) -> None:
        with self.assertLogs("ingots", "ERROR") as logs:
            code, _, _ = self.run_perf("failing", "smoke", FAILING_IS_SILENT="on")
        self.assertEqual(code, 1)
        self.assertIn("failing: no action measured", "\n".join(logs.output))

    def test_the_error(self) -> None:
        error = SmokeFailedError.for_errors("duel", ("invite: KeyError",))
        self.assertEqual(
            (error.scenario, error.errors), ("duel", ("invite: KeyError",))
        )


class NoGroupPerf(PerfUnit[None]):
    pass


class NoGroupProject(ScenariosProject):
    perf = Slot(NoGroupPerf)


class EchoGroup(LoadGroup[None]):
    pass


class PlainConfigsPerf(PerfUnit[None]):
    group = EchoGroup


class PlainConfigsProject(Project):
    perf = Slot(PlainConfigsPerf)


class BareSeed(CsvSeed):  # type: ignore[type-arg]
    pass


class BarePerf(PerfUnit[t.Any]):
    group = EchoGroup
    seed = Slot(BareSeed)


class BareProject(ScenariosProject):
    perf = Slot(BarePerf)


class PerfUnitTestCase(TestCase):
    def test_a_unit_without_its_group(self) -> None:
        with self.assertRaisesRegex(TypeError, "NoGroupPerf: no group of clients"):
            project = NoGroupProject()
            project.perf

    def test_a_project_without_the_configs_of_a_run(self) -> None:
        with self.assertRaisesRegex(TypeError, "no PerfConfigs"):
            project = PlainConfigsProject()
            project.perf

    def test_a_unit_without_the_type_of_its_rows(self) -> None:
        with self.assertRaisesRegex(TypeError, "BareSeed: no type of the rows"):
            project = BareProject()
            project.perf.seed._get_row_type()

    def test_a_run_of_now_by_default(self) -> None:
        project = BareProject()
        run = project.perf._get_run()
        self.assertRegex(run, r"^\d{8}-\d{6}-")

    def test_the_project_of_a_client_gone(self) -> None:
        from ingots.perf import LoadClient

        class Client(LoadClient[Project, EchoGroup]):
            @t.override
            async def run(self) -> None:
                pass

        client = Client(BareProject(), EchoGroup(None, Recorder(0, 1)))
        with self.assertRaisesRegex(ReferenceError, "Client: the project is gone"):
            client.project


class PointsTestCase(TestCase):
    def test_a_part_round_trip(self) -> None:
        part = PointPart((Call("echo", 0.5), Call("echo", 0.1, "KeyError")), 1.5)
        self.assertEqual(PointPart.load(part.dump()), part)

    def test_the_metrics_of_the_actions(self) -> None:
        calls = [
            Call("echo", 0.001),
            Call("echo", 0.002, "KeyError"),
            Call("ping", 0.01),
        ]
        measured = measure_actions(calls, duration=2.0, min_calls=2)
        self.assertEqual(measured["echo"]["calls"], "1")
        self.assertEqual(measured["echo"]["rps"], "0.5")
        self.assertEqual(measured["echo"]["errors_KeyError"], "1")
        self.assertEqual(measured["echo"]["void"], "calls 1")
        self.assertNotIn("p50_ms", measured["ping"])

    def test_the_cgroups(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pathlib.Path(directory, "cpu.stat").write_text("usage_usec 1500000\n")
            self.assertEqual(read_cgroups([f"redis={directory}"]), {"redis": 1.5})

    def test_the_swap_in(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vmstat = pathlib.Path(directory, "vmstat")
            with mock.patch.object(points, "VMSTAT", vmstat):
                self.assertIsNone(points.read_swap_in())  # off Linux
                vmstat.write_text("nr_free_pages 1\n")
                self.assertIsNone(points.read_swap_in())
                vmstat.write_text("nr_free_pages 1\npswpin 42\n")
                self.assertEqual(points.read_swap_in(), 42)

    def test_a_window_over_before_the_clients_start(self) -> None:
        recorder = Recorder(time.time() - 2, time.time() - 1)
        self.assertEqual(asyncio.run(run_clients([], recorder)), 0.0)

    def test_a_recorder_keeps_the_window(self) -> None:
        recorder = Recorder(10.0, 20.0)
        recorder.record("a", 9.0, 11.0)
        recorder.record("a", 11.0, 12.0)
        recorder.record("a", 19.0, 21.0)
        self.assertEqual([c.latency for c in recorder.calls], [1.0])
        self.assertTrue(math.isfinite(recorder.end))


class AnalyzeTestCase(PerfTestCase):
    def test_the_candidate_against_the_baseline(self) -> None:
        report = self.work / "reports/echo/r9.csv"
        report.parent.mkdir(parents=True)
        rows = [
            ("baseline", 1, "echo", 8, "rps", 100),
            ("baseline", 2, "echo", 8, "rps", 110),
            ("candidate", 1, "echo", 8, "rps", 130),
            ("candidate", 2, "echo", 8, "rps", 140),
            ("baseline", 1, "echo", 8, "p50_ms", 2),
            ("baseline", 2, "echo", 8, "p50_ms", 3),
            ("candidate", 1, "echo", 8, "p50_ms", 2.5),
            ("candidate", 2, "echo", 8, "p50_ms", 2.4),
            ("candidate", 1, "echo", 8, "void", "calls 3"),
            ("candidate", 1, "echo", 16, "rps", 150),
            ("baseline", 1, "point", 16, "cpu_ms_per_call", 1),
            ("candidate", 1, "point", 16, "load_cpu", 0.1),
        ]
        with report.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["role", "round", "action", "groups", "metric", "value"])
            writer.writerows(rows)
        code, out, err = self.run_perf("echo", "analyze", "r9")
        self.assertEqual(code, 0, err)
        self.assertEqual(
            out.splitlines(),
            [
                "echo, r9: baseline -> candidate",
                "echo 8 p50_ms: 2.500 -> 2.450 (-2.0%) void in candidate",
                "echo 8 rps: 105.000 -> 135.000 (+28.6%)* void in candidate",
                "echo 16 rps: the candidate alone",
                "point 16 cpu_ms_per_call: the baseline alone",
            ],
        )


class CsvReportTestCase(TestCase):
    def test_points_appended_and_merged_into_one_run(self) -> None:
        project = BareProject()
        report = project.perf.report
        with tempfile.TemporaryDirectory() as directory:
            csv_path = pathlib.Path(directory, "run.csv")
            ini_path = pathlib.Path(directory, "run.ini")
            row = ReportRow(
                role="baseline", round=1, action="a", groups=1, metric="m", value="x"
            )
            report.append(csv_path, [row])
            report.append(csv_path, [row])
            report.write_run(
                ini_path, {"run": {"A": "1"}, "role baseline": {"R": "v1"}}
            )
            report.write_run(
                ini_path, {"run": {"A": "2"}, "role candidate": {"R": "tree"}}
            )
            self.assertEqual(csv_path.read_text().count("\n"), 3)
            run = configparser.ConfigParser(interpolation=None)
            run.read(ini_path)
        self.assertEqual(run["run"]["A"], "2")
        self.assertEqual(run["role baseline"]["R"], "v1")


class MainTestCase(TestCase):
    def run_main(self, *argv: str) -> int:
        with (
            mock.patch.object(sys, "argv", ["ingots.perf", *argv]),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as caught,
        ):
            main()
        return t.cast(int, caught.exception.code)

    def test_the_usage(self) -> None:
        self.assertEqual(self.run_main(), 2)
        self.assertEqual(self.run_main("--help"), 0)

    def test_a_module_refused(self) -> None:
        self.assertEqual(self.run_main(str(SCENARIOS / "missing.py")), 1)

    def test_a_command(self) -> None:
        code = self.run_main(
            str(SCENARIOS / "echo.py"),
            *(
                "--config",
                "IS_CONFIGURE_LOGGING=off",
                "--config",
                "IS_PRINT_CONFIGS=off",
            ),
            *("perf", "plan"),
        )
        self.assertEqual(code, 0)
