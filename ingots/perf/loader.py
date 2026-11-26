"""The module of a scenario, loaded by its path."""

__all__ = ("find_configs_files", "get_stand", "load_scenario", "run_scenario")

import argparse
import importlib.util
import re
import sys
import typing as t
from pathlib import Path

from ingots.defaults import Project
from ingots.defaults.cli import CommandRunner

from .errors import ScenarioModuleError

if t.TYPE_CHECKING:
    from collections.abc import Sequence

    from . import PerfStandProject


def load_scenario(path: "Path") -> "type[PerfStandProject]":
    """
    The ``PerfProject`` of the module of a scenario, loaded by its path, not
    as a package, so that ``scenarios/`` of a stand does not shadow the
    package ``scenarios`` of its example. The stand, the directory above
    ``scenarios/``, joins the end of the path of imports: its modules, the
    base its scenarios share, import, the packages of the example first.

    :raises ScenarioModuleError: no such module, or it gives no
        :class:`~ingots.perf.PerfStandProject` whose slot ``perf`` is a
        :class:`~ingots.perf.PerfUnit`.
    """
    from . import PerfStandProject, PerfUnit

    if not path.is_file():
        raise ScenarioModuleError.for_module(str(path), "no such module")
    stand = str(path.resolve().parent.parent)
    if stand not in sys.path:
        sys.path.append(stand)
    name = "ingots_perf_scenario_" + re.sub(r"\W", "_", path.stem)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # the dataclasses of its rows resolve by it
    spec.loader.exec_module(module)
    project_cls = getattr(module, "PerfProject", None)
    if not (
        isinstance(project_cls, type) and issubclass(project_cls, PerfStandProject)
    ):
        raise ScenarioModuleError.for_module(
            str(path), "no PerfProject, a PerfStandProject"
        )
    if project_cls.perf.cls is PerfUnit:
        raise ScenarioModuleError.for_module(
            str(path), "PerfProject gives no PerfUnit of its own in its slot perf"
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
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--configs-file", type=Path, action="append", default=[])
    known, rest = parser.parse_known_args(argv)
    given = {file.resolve() for file in known.configs_file}
    found = [file for file in find_configs_files(path) if file.resolve() not in given]
    files = [
        arg
        for file in (*found, *known.configs_file)
        for arg in ("--configs-file", str(file))
    ]
    return CommandRunner(load_scenario(path), [*files, *rest]).run()


def get_stand(project: Project) -> Path:
    """
    The stand of the scenario of a project, the directory above its
    ``scenarios/``: the relative paths of its configs are of it.
    """
    module = sys.modules[type(project).__module__]
    return Path(t.cast(str, module.__file__)).parent.parent
