"""The configs of a run of the load."""

__all__ = ("PerfConfigs", "iter_perf_configs")

import typing as t

from ingots.defaults.settings.configs import (
    BaseConfig,
    Configs,
    FloatConfig,
    IntConfig,
    ListConfig,
    StrConfig,
    iter_configs,
)

if t.TYPE_CHECKING:
    from collections.abc import Iterator


class PerfConfigs(Configs):
    """
    The configs of a run, ``PERF_*``, joined to those of the client the
    scenario loads: ``class GamePerfConfigs(ScenariosConfigs, PerfConfigs)``.
    The stand gives them in its ``perf.ini``, the scenario in its own
    ``scenarios/<name>.ini``, both by ``--configs-file``; the command line
    overrides them. The runner reads them resolved by ``perf plan``.
    """

    # the run: what the runner brings up and how many times
    PERF_EXAMPLE = StrConfig("")
    PERF_BASELINE = StrConfig("latest")
    PERF_CANDIDATE = StrConfig("tree")
    PERF_ROUNDS = IntConfig(3)
    PERF_GROUPS = ListConfig(int, (1, 2, 4, 8, 16))
    PERF_LOAD_CPUS = StrConfig("")
    PERF_SYSTEM_CPUS = StrConfig("")

    # a point: its processes, its window, what voids it
    PERF_LOAD_PROCS = IntConfig(4)
    PERF_WARMUP = FloatConfig(10.0)
    PERF_DURATION = FloatConfig(30.0)
    PERF_MIN_CALLS = IntConfig(20)
    PERF_MAX_LOAD_CPU = FloatConfig(0.9)

    # where the files go: the seed and the parts of a point, the reports
    PERF_WORK = StrConfig(".")
    PERF_SEED_FILE = StrConfig("")
    PERF_REPORTS = StrConfig("reports")

    # what the runner tells a point of the run, the role and the host
    PERF_RUN = StrConfig("")
    PERF_ROLE = StrConfig("candidate")
    PERF_ROUND = IntConfig(1)
    PERF_REF = StrConfig("")
    PERF_COMMIT = StrConfig("")
    PERF_SERVERS = StrConfig("")
    PERF_HOST_STATE = StrConfig("")
    PERF_CGROUPS = ListConfig(str)


def iter_perf_configs() -> "Iterator[BaseConfig[t.Any]]":
    """The configs of a run, those :class:`PerfConfigs` declares, by name."""
    for config in iter_configs(PerfConfigs):
        if config.name in vars(PerfConfigs):
            yield config
