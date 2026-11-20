"""
Runs a scenario of the load: ``python -m ingots.perf <module> [options]
perf <command>``, the ``PerfProject`` of the module at that path.
"""

import argparse
import logging
import sys
from pathlib import Path

from ingots.defaults.logging import configure_startup_logging

from .errors import ScenarioModuleError
from .loader import run_scenario

logger = logging.getLogger("ingots.perf")


def main() -> None:
    configure_startup_logging()
    parser = argparse.ArgumentParser(
        prog="python -m ingots.perf",
        description="Runs a command of the PerfProject of a scenario module.",
        allow_abbrev=False,
    )
    parser.add_argument("module", type=Path, help="the module of the scenario")
    parser.add_argument(
        "argv",
        nargs=argparse.REMAINDER,
        help="the options of its project, then perf <command>",
    )
    args = parser.parse_args()
    try:
        code = run_scenario(args.module, args.argv)
    except ScenarioModuleError as error:
        logger.error("%s", error)
        sys.exit(1)
    sys.exit(code)


if __name__ == "__main__":
    main()
