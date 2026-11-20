"""The analysis of a report: the candidate against the baseline."""

__all__ = ("Comparison", "MedianAnalysis", "Rounds", "Series")

import dataclasses
import statistics
import typing as t

from ingots.puer import Entity

if t.TYPE_CHECKING:
    from collections.abc import Sequence

    from .reports import ReportRow


@dataclasses.dataclass(frozen=True, slots=True, order=True)
class Series:
    """A metric of an action at a point, compared across the roles."""

    action: str
    groups: int
    metric: str


@dataclasses.dataclass(slots=True)
class Rounds:
    """The values of a series in the rounds of a role; void, a round of it was."""

    values: tuple[float, ...] = ()
    is_void: bool = False


@dataclasses.dataclass(slots=True)
class Comparison:
    """The rounds of a series, the baseline's and the candidate's."""

    baseline: Rounds = dataclasses.field(default_factory=Rounds)
    candidate: Rounds = dataclasses.field(default_factory=Rounds)


class MedianAnalysis(Entity):
    """
    The candidate against the baseline in a report, a line a point and
    metric: the median of the rounds of each role, the change, marked ``*``
    when the rounds of the roles do not overlap, a change beyond their
    spread; a point of the candidate alone, the baseline never measured it,
    told so, not a regression. A scenario shapes its own by a subclass in
    the slot ``analysis`` of its unit.
    """

    # the metrics compared, of the actions and of the point
    METRICS: t.ClassVar[tuple[str, ...]] = (
        "rps",
        "p50_ms",
        "p95_ms",
        "cpu_ms_per_call",
    )

    def analyze(self, rows: "Sequence[ReportRow]") -> "Sequence[str]":
        """The lines of the analysis of the rows of a report."""
        return [
            self._tell(series, comparison)
            for series, comparison in sorted(self._compare(rows).items())
        ]

    def _compare(self, rows: "Sequence[ReportRow]") -> dict[Series, Comparison]:
        """The comparisons of the series of the rows, void the rounds told so."""
        comparisons: dict[Series, Comparison] = {}
        for row in rows:
            if row.metric in self.METRICS:
                series = Series(row.action, row.groups, row.metric)
                comparison = comparisons.setdefault(series, Comparison())
                if rounds := select_rounds(comparison, row.role):
                    rounds.values += (float(row.value),)
        for row in rows:
            if row.metric != "void" or not row.value:
                continue
            for series, comparison in comparisons.items():
                is_point = series.action == row.action and series.groups == row.groups
                if is_point and (rounds := select_rounds(comparison, row.role)):
                    rounds.is_void = True
        return comparisons

    def _tell(self, series: Series, comparison: Comparison) -> str:
        """The line of a series."""
        told = f"{series.action} {series.groups} {series.metric}:"
        baseline, candidate = comparison.baseline, comparison.candidate
        if not baseline.values:
            return f"{told} the candidate alone"
        if not candidate.values:
            return f"{told} the baseline alone"
        old = statistics.median(baseline.values)
        new = statistics.median(candidate.values)
        change = (new / old - 1) * 100 if old else 0.0
        apart = max(baseline.values) < min(candidate.values) or max(
            candidate.values
        ) < min(baseline.values)
        marks = "*" if apart and len(baseline.values) > 1 else ""
        voided = [
            role
            for role, rounds in (("baseline", baseline), ("candidate", candidate))
            if rounds.is_void
        ]
        if voided:
            marks += f" void in {', '.join(voided)}"
        return f"{told} {old:.3f} -> {new:.3f} ({change:+.1f}%){marks}"


def select_rounds(comparison: Comparison, role: str) -> Rounds | None:
    """The rounds of the role in the comparison; none for a role not compared."""
    match role:
        case "baseline":
            return comparison.baseline
        case "candidate":
            return comparison.candidate
    return None
