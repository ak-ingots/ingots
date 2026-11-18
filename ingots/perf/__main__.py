"""
Runs a scenario of the load: ``python -m ingots.perf <module> [options]
perf <command>``, the ``PerfProject`` of the module at that path.
"""

import logging
import sys
from pathlib import Path

from ingots.defaults.logging import configure_startup_logging

from .errors import ScenarioModuleError
from .loader import run_scenario

logger = logging.getLogger("ingots.perf")

USAGE = "usage: python -m ingots.perf <module> [options] perf <command>"


def main() -> None:
    configure_startup_logging()
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        print(USAGE, file=sys.stderr)
        sys.exit(2)
    try:
        code = run_scenario(Path(sys.argv[1]), sys.argv[2:])
    except ScenarioModuleError as error:
        logger.error("%s", error)
        sys.exit(1)
    sys.exit(code)


if __name__ == "__main__":
    main()
