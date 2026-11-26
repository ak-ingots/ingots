#!/usr/bin/env -S uv run python
"""
Runs the demo: ``./manage.py demo greet --name=Ann``, ``./manage.py
components run-forever --component=greetings.clock``; ``./manage.py
completion bash`` prints the completion of bash for it. The shebang runs it
by ``uv run``, in the environment of the project uv finds from the
directory at hand, so within the checkout; ``python manage.py`` runs it in
the environment active.
"""

import sys

from ingots.defaults.cli import CommandRunner
from ingots.defaults.logging import configure_startup_logging

from project import DemoProject


def main() -> None:
    configure_startup_logging()
    sys.exit(CommandRunner(DemoProject).run())


if __name__ == "__main__":
    main()
