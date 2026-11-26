"""The data of the command line."""

__all__ = ("CliCompletion", "ProjectCliArgs")

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class CliCompletion:
    """
    What completes the value of an option in a shell: ``words``, or the
    paths of the files; ``is_spaced`` off when the value goes on after the
    word, as after the ``=`` of ``--config NAME=``. Nothing by default.
    """

    words: tuple[str, ...] = ()
    files: bool = False
    is_spaced: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCliArgs:
    """
    The overrides of the configs on the command line. Keyword-only, so the
    arguments of a subclass add fields of their own, with or without
    defaults.
    """

    configs: tuple[tuple[str, str], ...] = ()
    configs_files: tuple[Path, ...] = ()
