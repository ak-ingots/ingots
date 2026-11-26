# The load

{py:mod}`ingots.perf` is what is loaded and how, against a target already
up: a scenario, its clients, a point of the load, its report. How the
target is brought up and down is its stand's; how a run is carried out on
a host, the roles, the cores, the rounds, is a runner's; both outside the
framework. The runner reads the configs of the run from `perf plan` and
calls `perf seed`, `perf point` and `perf analyze`.

## A stand and its scenarios

A stand is a directory: `perf.ini`, the configs of every scenario,
`scenarios/<name>.py` a scenario each, `scenarios/<name>.ini` the configs
of one, `reports/` the reports of the runs. A scenario is a module giving
`PerfProject`: the project of the client it loads, a
{py:class}`~ingots.perf.PerfStandProject`, with the unit `perf`, a
{py:class}`~ingots.perf.PerfUnit`, and the configs of a run,
{py:class}`~ingots.perf.PerfConfigs`, joined to those of the client:

The paths of the configs, `PERF_WORK` (`work` by default), `PERF_SEED_FILE`
and `PERF_REPORTS` (`reports`), are of the stand when relative; a stand
keeps `work/` and `reports/dry/` out of git. A scenario imports the
project of its client as the stand runs it: from the directory of its
example, say, so that the packages of the example import. The modules of
the stand import too, `project.py` beside `scenarios/` the base they share:
the stand is a project of its own, apart from its example. That base
inherits {py:class}`~ingots.perf.PerfStandProject` first, which puts the
commands `perf` on its command line; a client of an addon with commands of
its own joins its `cli` with {py:class}`~ingots.perf.PerfCliUnit`.

```python
import dataclasses

from ingots.perf import CsvSeed, LoadClient, LoadGroup, PerfConfigs, PerfUnit
from ingots.puer import Slot


class GamePerfConfigs(ScenariosConfigs, PerfConfigs): ...


class GamePerfSettings(ScenariosSettingsUnit):
    configs = Slot(GamePerfConfigs)


@dataclasses.dataclass
class SeededPlayer:                      # a row of seed.csv
    nickname: str
    token: str


class Player(LoadClient["PerfProject", "PlayerGroup"]):
    async def asyncSetUp(self) -> None:  # unmeasured
        self.token = self.group.seeded.token

    async def run(self) -> None:         # again and again
        async with self.measure("get-own-profile"):
            await self.project.grpc.clients.game.get_own_profile(self.token)


class PlayerGroup(LoadGroup[SeededPlayer]):
    clients = (Player,)


class PlayersSeed(CsvSeed[SeededPlayer]):
    project: "PerfProject"

    async def _make(self, groups: int) -> list[SeededPlayer]:
        return [await sign_up_and_in(self.project) for _ in range(groups)]


class OwnProfilePerf(PerfUnit[SeededPlayer]):
    group = PlayerGroup
    seed = Slot(PlayersSeed)


class PerfProject(ScenariosProject):
    settings = Slot(GamePerfSettings)
    perf = Slot(OwnProfilePerf)
```

- A {py:class}`~ingots.perf.LoadClient` is a user of the application, an
  instance a client: its `asyncSetUp()` unmeasured, then its `run()` again
  and again until the window of the point is over; it names what it
  measures, `measure("get-own-profile")`, an error of the block counted
  by the name of its class.
- A {py:class}`~ingots.perf.LoadGroup` is the clients that meet, one of
  each class of its `clients`, a class twice for two, and what they share:
  the row of the seed, the state its subclass declares, set up by its
  `asyncSetUp()`, a time one client starts, `self.group.start("invite",
  key)`, and another finishes, `finish("invite", key)`, measured as an
  action. A group runs in one process of the load.
- A {py:class}`~ingots.perf.CsvSeed` in the slot `seed` of the unit makes
  what the scenario needs ahead by its `_make()`, through the API of the
  application, rows of a dataclass, `CsvSeed[Row]`, of the rows of the
  unit, `PerfUnit[Row]`, as mypy checks; `perf seed` writes them into
  `seed.csv` of `PERF_WORK`, a point reads them back by the annotations of
  their fields, group `i` taking row `i` in turn. A scenario that seeds
  nothing keeps the default, which makes no row.

## The commands

`python -m ingots.perf <module> [options] perf <command>` loads the
module by its path, not as a package, and runs the command of its
`PerfProject`, configured as any project. The configs files of the
scenario are found beside it, those there are: `perf.ini` of the stand,
above `scenarios/`, then `scenarios/<name>.ini`; then come the files of
`--configs-file`, the environment and `--config PERF_DURATION=60`, the
later winning.

- `perf plan`: the configs of a run resolved, `PERF_*`, a line each,
  `NAME=value` quoted for the shell, a list its items apart by spaces:
  `eval "$(python -m ingots.perf ... perf plan)"`.
- `perf seed`: the rows of the largest point of `PERF_GROUPS`.
- `perf point --groups N`: a point: `PERF_LOAD_PROCS` processes of the load,
  `perf load`, the groups spread over them; each sets its clients up and
  tells it is ready, then all start at once, warm up `PERF_WARMUP` seconds
  and are measured `PERF_DURATION`; the CPU of the services in
  `PERF_CGROUPS`, `name=/sys/fs/cgroup/...`, and the swap of the host are
  read at the window. The rows go to `reports/<scenario>/<PERF_RUN>.csv`,
  the run, the host and the role to its `.ini`.
- `perf analyze RUN`: the report of a run, the candidate against the
  baseline, a line a point and metric: the median of the rounds of each
  role and the change, marked `*` when the rounds of the roles do not
  overlap; a point the baseline never measured told so, not a regression.
  The slot `analysis` of the unit holds a
  {py:class}`~ingots.perf.MedianAnalysis`, a scenario gives its own.
- `perf smoke`: a point dry, in the process: a group, a run of each client;
  it fails when an action erred or none was measured. Its report goes to
  `reports/dry/`.

A row of a report is a metric of an action of a point: by each action the
calls, the calls a second, p50, p95, p99 in milliseconds, the errors by
their names and why it is void, fewer calls than `PERF_MIN_CALLS`; by the
point, action `point`, the CPU of the load, of each service and of the
services a call, the pages swapped in.
