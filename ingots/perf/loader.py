"""The module of a scenario, loaded by its path."""

__all__ = ("find_configs_files", "load_scenario", "run_scenario")

import importlib.util
import re
import sys
import typing as t

from ingots.defaults import Project
from ingots.puer.cli import CommandRunner

from .errors import ScenarioModuleError

from pathlib import Path

if t.TYPE_CHECKING:
    from collections.abc import Sequence


def load_scenario(path: "Path") -> type[Project]:
    """
    The ``PerfProject`` of the module of a scenario, loaded by its path, not
    as a package, so that ``scenarios/`` of a stand does not shadow the
    package ``scenarios`` of its example.

    :raises ScenarioModuleError: no such module, or it gives no project
        whose slot ``perf`` is a :class:`~ingots.perf.PerfUnit`.
    """
    from . import PerfUnit

    if not path.is_file():
        raise ScenarioModuleError.for_module(str(path), "no such module")
    name = "ingots_perf_scenario_" + re.sub(r"\W", "_", path.stem)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # the dataclasses of its rows resolve by it
    spec.loader.exec_module(module)
    project_cls = getattr(module, "PerfProject", None)
    if not (isinstance(project_cls, type) and issubclass(project_cls, Project)):
        raise ScenarioModuleError.for_module(str(path), "no PerfProject, a project")
    perf_slot = getattr(project_cls, "perf", None)
    if not issubclass(getattr(perf_slot, "cls", type(None)), PerfUnit):
        raise ScenarioModuleError.for_module(
            str(path), "PerfProject has no slot perf of a PerfUnit"
        )
    return project_cls


def find_configs_files(path: Path) -> tuple[Path, ...]:
    """
    The configs files of the module of a scenario, those there are: the
    stand's, ``perf.ini`` above ``scenarios/``, then the scenario's,
    ``<name>.ini`` beside it.
    """
    candidates = (path.parent.parent / "perf.ini", path.with_suffix(".ini"))
    return tuple(candidate for candidate in candidates if candidate.is_file())


def run_scenario(path: Path, argv: "Sequence[str]") -> int:
    """
    Runs the command of ``argv`` of the ``PerfProject`` of the module of a
    scenario, the configs files of :func:`find_configs_files` first, so that
    those of ``argv``, the environment and ``--config`` win over them; a
    file given again, as a point gives its own to its processes, not twice.
    """
    given = {
        Path(argv[index + 1]).resolve()
        for index, arg in enumerate(argv[:-1])
        if arg == "--configs-file"
    }
    found = [
        arg
        for file in find_configs_files(path)
        if file.resolve() not in given
        for arg in ("--configs-file", str(file))
    ]
    return CommandRunner(load_scenario(path), [*found, *argv]).run()
