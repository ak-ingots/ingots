"""The commands of the load: ``perf seed``, ``point``, ``load``, ``smoke``, ``plan``."""

__all__ = (
    "AnalyzeCliArgs",
    "AnalyzeCommand",
    "LoadCliArgs",
    "LoadCommand",
    "PlanCommand",
    "PointCliArgs",
    "PointCommand",
    "SeedCommand",
    "SmokeCommand",
)

import argparse
import asyncio
import contextlib
import logging
import math
import os
import shlex
import sys
import time
import typing as t
from dataclasses import dataclass
from pathlib import Path

from ingots.puer.cli import BaseCommand

from .clients import Recorder
from .configs import iter_perf_configs
from .loader import get_stand
from .errors import SmokeFailedError
from .points import POINT_ACTION, PointPart, measure_actions, read_cgroups
from .points import read_swap_in, show
from .reports import ReportRow, show_config

if t.TYPE_CHECKING:
    from collections.abc import Sequence

    from ingots.defaults import Project

    from . import PerfUnit
    from .clients import LoadClient

logger = logging.getLogger(__name__)

# what a process of the load tells the point once its clients are set up
READY = b"ready"

# the time the start takes to reach the processes of the load, in seconds
START_MARGIN = 0.2


class BasePerfCommand(BaseCommand):
    """A command of the unit ``perf``, its scenario its parent's."""

    parent: "PerfUnit[t.Any]"
    project: "Project"


class SeedCommand(BasePerfCommand):
    """``perf seed``: the rows the scenario needs ahead, into ``seed.csv``."""

    cli_name = "seed"
    cli_description = "Seeds what the scenario needs ahead, for its largest point."

    @t.override
    async def _run(self) -> None:
        unit = self.parent
        rows = await unit.seed.write(max(unit._get_configs().PERF_GROUPS, default=1))
        logger.info("seeded %d rows into %s", rows, unit.seed.path)


@dataclass(frozen=True, slots=True, kw_only=True)
class PointCliArgs:
    """The groups of a point."""

    groups: int


class PointCommand(BasePerfCommand):
    """
    ``perf point --groups N``: a point of the load against the target up.
    Starts the processes of the load, ``perf load``, the groups spread over
    them; once each has set its clients up, tells them all the start; reads
    the CPU of the services and the swap of the host at the window; merges
    what the processes measured and appends the rows to the report of the
    run, its INI told of the run, the host and the role.
    """

    cli_name = "point"
    cli_description = "Runs a point of the load and appends it to the report."
    cli_args: PointCliArgs

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--groups",
            dest="perf_point_groups",
            type=int,
            required=True,
            metavar="N",
            help="the groups of clients of the point",
        )

    @t.override
    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> PointCliArgs:
        return PointCliArgs(groups=namespace.perf_point_groups)

    @t.override
    async def _run(self) -> None:
        unit = self.parent
        configs = unit._get_configs()
        groups = self.cli_args.groups
        procs = max(1, min(groups, configs.PERF_LOAD_PROCS))
        work = get_stand(self.project) / configs.PERF_WORK
        work.mkdir(parents=True, exist_ok=True)
        outs = [work / f"part-{part}.json" for part in range(procs)]
        swap_in = read_swap_in()
        children = [
            await asyncio.create_subprocess_exec(
                *self._get_load_argv(groups, part, procs, out),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
            )
            for part, out in enumerate(outs)
        ]
        try:
            for child in children:
                await wait_ready(child)
            start = time.time() + START_MARGIN
            for child in children:
                assert child.stdin is not None
                child.stdin.write(f"{start}\n".encode())
                await child.stdin.drain()
            window = start + configs.PERF_WARMUP
            await asyncio.sleep(window - time.time())
            cpu_before = read_cgroups(configs.PERF_CGROUPS)
            await asyncio.sleep(window + configs.PERF_DURATION - time.time())
            cpu_after = read_cgroups(configs.PERF_CGROUPS)
            codes = [await child.wait() for child in children]
        finally:
            for child in children:
                if child.returncode is None:
                    child.kill()
                    await child.wait()
        if any(codes):
            raise RuntimeError(f"a process of the load failed: exit codes {codes}")
        parts = [PointPart.load(out.read_text()) for out in outs]
        swap_after = read_swap_in()
        swapped = (swap_after or 0) - (swap_in or 0)
        services = {name: cpu_after[name] - cpu_before[name] for name in cpu_after}
        rows = self._build_rows(groups, parts, services, swapped)
        unit.report.append_point(unit._get_report_path(), rows)

    def _get_load_argv(
        self, groups: int, part: int, parts: int, out: Path
    ) -> list[str]:
        """The command line of a process of the load, the project's own options."""
        module = sys.modules[type(self.project).__module__]
        argv = [sys.executable, "-m", "ingots.perf", t.cast(str, module.__file__)]
        args = self.project.cli_args
        for path in args.configs_files:
            argv += ["--configs-file", str(path)]
        for name, value in args.configs:
            argv += ["--config", f"{name}={value}"]
        argv += ["--config", "IS_PRINT_CONFIGS=off"]
        return [
            *argv,
            *self.parent.full_name.split("."),
            "load",
            *("--groups", str(groups), "--part", str(part), "--parts", str(parts)),
            *("--out", str(out)),
        ]

    def _build_rows(
        self,
        groups: int,
        parts: list[PointPart],
        services: dict[str, float],
        swapped: int,
    ) -> list[ReportRow]:
        configs = self.parent._get_configs()
        duration = configs.PERF_DURATION
        calls = [call for part in parts for call in part.calls]
        measured = measure_actions(calls, duration, configs.PERF_MIN_CALLS)
        load_cpu = sum(part.cpu for part in parts) / duration / count_cpus()
        void = []
        if load_cpu > configs.PERF_MAX_LOAD_CPU:
            void.append(f"load-cpu {load_cpu:.2f}")
        if swapped:
            void.append(f"swap-in {swapped}")
        point: dict[str, str] = {"load_cpu": show(load_cpu), "swap_in": str(swapped)}
        for name, cpu in services.items():
            point[f"cpu_cores_{name}"] = show(cpu / duration)
        succeeded = sum(1 for call in calls if not call.error)
        if services and succeeded:
            point["cpu_ms_per_call"] = show(sum(services.values()) * 1000 / succeeded)
        point["void"] = "; ".join(void)
        measured[POINT_ACTION] = point
        return [
            ReportRow(
                role=configs.PERF_ROLE,
                round=configs.PERF_ROUND,
                action=action,
                groups=groups,
                metric=metric,
                value=value,
            )
            for action, metrics in measured.items()
            for metric, value in metrics.items()
        ]


async def wait_ready(child: asyncio.subprocess.Process) -> None:
    """Reads the output of a process of the load until it tells it is ready."""
    assert child.stdout is not None
    while line := await child.stdout.readline():
        if line.strip() == READY:
            return
    raise RuntimeError(
        f"a process of the load ended before it was ready: {await child.wait()}"
    )


def count_cpus() -> int:
    """The CPUs the process may run on, those of the load under its scope."""
    return len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else 1


@dataclass(frozen=True, slots=True, kw_only=True)
class LoadCliArgs:
    """The share of a process of the load in its point."""

    groups: int
    part: int
    parts: int
    out: Path


class LoadCommand(BasePerfCommand):
    """
    ``perf load``, started by ``perf point``: sets up its groups, those of
    the point whose index is its part modulo the parts, tells it is ready,
    waits for the start on its input, runs its clients until the window is
    over, then writes what it measured in the window to ``--out``.
    """

    cli_name = "load"
    cli_description = "A process of a point of the load; perf point starts it."
    cli_args: LoadCliArgs

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        for name in ("groups", "part", "parts"):
            parser.add_argument(
                f"--{name}", dest=f"perf_load_{name}", type=int, required=True
            )
        parser.add_argument("--out", dest="perf_load_out", type=Path, required=True)

    @t.override
    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> LoadCliArgs:
        return LoadCliArgs(
            groups=namespace.perf_load_groups,
            part=namespace.perf_load_part,
            parts=namespace.perf_load_parts,
            out=namespace.perf_load_out,
        )

    @t.override
    async def _run(self) -> None:
        unit = self.parent
        configs = unit._get_configs()
        args = self.cli_args
        rows = unit.seed.read()
        recorder = Recorder(math.inf, math.inf)
        clients: list[LoadClient[t.Any, t.Any]] = []
        for index in range(args.part, args.groups, args.parts):
            clients += await unit._create_group(index, rows, recorder)
        print(READY.decode(), flush=True)
        start = float(await asyncio.to_thread(sys.stdin.readline))
        recorder.start = start + configs.PERF_WARMUP
        recorder.end = recorder.start + configs.PERF_DURATION
        await asyncio.sleep(start - time.time())
        cpu = await run_clients(clients, recorder)
        args.out.write_text(PointPart(tuple(recorder.calls), cpu).dump())


async def run_clients(
    clients: "Sequence[LoadClient[t.Any, t.Any]]", recorder: Recorder
) -> float:
    """
    Runs the clients again and again until the window of the recorder is
    over, a client then cancelled, waiting on its rival or not; the CPU of
    the process in the window.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + recorder.end - time.time()

    async def run(client: "LoadClient[t.Any, t.Any]") -> None:
        while True:
            await client.run()

    # the CPU at the start of the window; at its end, once the clients are
    # cancelled: a task ending at the deadline would be cancelled with them
    started: list[float] = []

    async def mark_start() -> None:
        await asyncio.sleep(recorder.start - time.time())
        started.append(time.process_time())

    with contextlib.suppress(TimeoutError):
        async with asyncio.timeout_at(deadline), asyncio.TaskGroup() as tasks:
            tasks.create_task(mark_start())
            for client in clients:
                tasks.create_task(run(client))
    return time.process_time() - started[0] if started else 0.0


class SmokeCommand(BasePerfCommand):
    """
    ``perf smoke``: a point dry, against the target up, in the process: a
    group seeded, its clients set up, a run of each; fails when an action
    erred or none was measured. Its report goes to ``dry/`` of the reports,
    out of git.
    """

    cli_name = "smoke"
    cli_description = "Runs a group of the scenario once; fails on an error."

    @t.override
    async def _run(self) -> None:
        unit = self.parent
        configs = unit._get_configs()
        recorder = Recorder(0, math.inf)
        async with asyncio.timeout(configs.PERF_DURATION):
            clients = await unit._create_group(0, await unit.seed._make(1), recorder)
            await asyncio.gather(*(client.run() for client in clients))
        calls = recorder.calls
        errors = tuple(f"{call.action}: {call.error}" for call in calls if call.error)
        scenario = unit._get_scenario()
        if errors or not calls:
            raise SmokeFailedError.for_errors(scenario, errors)
        measured = measure_actions(calls, configs.PERF_DURATION, 1)
        rows = [
            ReportRow(
                role="dry", round=1, action=action, groups=1, metric=metric, value=value
            )
            for action, metrics in measured.items()
            for metric, value in metrics.items()
        ]
        reports = get_stand(self.project) / configs.PERF_REPORTS
        path = reports / "dry" / scenario / f"{unit._get_run()}.csv"
        unit.report.append(path, rows)
        logger.info(
            "%s: dry, %d calls of %s", scenario, len(calls), ", ".join(measured)
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalyzeCliArgs:
    """The run analyzed."""

    run: str


class AnalyzeCommand(BasePerfCommand):
    """
    ``perf analyze RUN``: the report of a run of the scenario, the
    candidate against the baseline, by the analysis of the unit.
    """

    cli_name = "analyze"
    cli_description = "Prints the candidate against the baseline in a report."
    cli_args: AnalyzeCliArgs

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "perf_analyze_run",
            metavar="RUN",
            help="the run, the name of its report: <date>-<time>-<host>",
        )

    @t.override
    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> AnalyzeCliArgs:
        return AnalyzeCliArgs(run=namespace.perf_analyze_run)

    @t.override
    async def _run(self) -> None:
        unit = self.parent
        reports = get_stand(self.project) / unit._get_configs().PERF_REPORTS
        path = reports / unit._get_scenario() / f"{self.cli_args.run}.csv"
        print(f"{unit._get_scenario()}, {self.cli_args.run}: baseline -> candidate")
        for line in unit.analysis.analyze(unit.report.read(path)):
            print(line)


class PlanCommand(BasePerfCommand):
    """
    ``perf plan``: the configs of a run resolved, ``PERF_*``, a line each,
    ``NAME=value`` quoted for the shell, a list its items apart by spaces,
    so that a runner takes them by ``eval`` and parses no file.
    """

    cli_name = "plan"
    cli_description = "Prints the configs of a run for the shell of a runner."

    @t.override
    async def _run(self) -> None:
        configs = self.parent._get_configs()
        for config in iter_perf_configs():
            text = show_config(getattr(configs, config.name))
            print(f"{config.name}={shlex.quote(text)}")
