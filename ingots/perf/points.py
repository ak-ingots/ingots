"""A point of the load: its parts, its metrics, the host around it."""

__all__ = (
    "POINT_ACTION",
    "PointPart",
    "measure_actions",
    "read_cgroups",
    "read_swap_in",
)

import dataclasses
import json
import statistics
import typing as t
from pathlib import Path

from .clients import Call

# the action of the rows of the point as a whole: the CPU, the host
POINT_ACTION = "point"

# where Linux tells the pages swapped in since its start
VMSTAT = Path("/proc/vmstat")


@dataclasses.dataclass(frozen=True, slots=True)
class PointPart:
    """What a process of the load measured: its calls, its CPU in the window."""

    calls: tuple[Call, ...]
    cpu: float

    @classmethod
    def load(cls, text: str) -> t.Self:
        """The part from its JSON."""
        data = json.loads(text)
        calls = tuple(
            Call(action, latency, error) for action, latency, error in data["calls"]
        )
        return cls(calls, data["cpu"])

    def dump(self) -> str:
        """The part as JSON, for the process of the point."""
        calls = [[call.action, call.latency, call.error] for call in self.calls]
        return json.dumps({"calls": calls, "cpu": self.cpu})


def measure_actions(
    calls: "t.Iterable[Call]", duration: float, min_calls: int
) -> dict[str, dict[str, str]]:
    """
    The metrics of each action: its calls, a second, p50, p95, p99 in
    milliseconds, its errors by their names, and why it is void, fewer
    calls than ``min_calls``.
    """
    by_action: dict[str, list[Call]] = {}
    for call in calls:
        by_action.setdefault(call.action, []).append(call)
    measured = {}
    for action, its_calls in sorted(by_action.items()):
        latencies = sorted(c.latency * 1000 for c in its_calls if not c.error)
        metrics: dict[str, object] = {
            "calls": len(latencies),
            "rps": round(len(latencies) / duration, 3),
        }
        if len(latencies) > 1:
            cuts = statistics.quantiles(latencies, n=100, method="inclusive")
            metrics |= {"p50_ms": cuts[49], "p95_ms": cuts[94], "p99_ms": cuts[98]}
        errors: dict[str, int] = {}
        for call in its_calls:
            if call.error:
                errors[call.error] = errors.get(call.error, 0) + 1
        metrics |= {f"errors_{name}": count for name, count in sorted(errors.items())}
        metrics["void"] = (
            f"calls {len(latencies)}" if len(latencies) < min_calls else ""
        )
        measured[action] = {name: show(value) for name, value in metrics.items()}
    return measured


def show(value: object) -> str:
    """A value of a metric as the report keeps it."""
    return str(round(value, 3)) if isinstance(value, float) else str(value)


def read_cgroups(cgroups: "t.Iterable[str]") -> dict[str, float]:
    """
    The CPU, in seconds, each cgroup used since its start, by its
    ``cpu.stat``; ``cgroups`` as ``name=/sys/fs/cgroup/...``.
    """
    usage = {}
    for item in cgroups:
        name, _, path = item.partition("=")
        for line in Path(path, "cpu.stat").read_text().splitlines():
            key, _, value = line.partition(" ")
            if key == "usage_usec":
                usage[name] = int(value) / 1_000_000
    return usage


def read_swap_in() -> int | None:
    """The pages swapped in since Linux started; none off Linux."""
    try:
        text = VMSTAT.read_text()
    except OSError:
        return None
    for line in text.splitlines():
        key, _, value = line.partition(" ")
        if key == "pswpin":
            return int(value)
    return None
