"""
Two projects of one host for the completion: a shop, its configs, a
component, a command with choices; a game, its own command. And bash, run
on the command line an operator typed.
"""

import argparse
import contextlib
import io
import re
import subprocess
import typing as t

from ingots.defaults import Project
from ingots.defaults.cli import CliUnit, CommandRunner, CommandsUnit
from ingots.defaults.cli import BaseCommand
from ingots.defaults.settings import SettingsUnit
from ingots.defaults.settings.configs import Configs, IntConfig
from ingots.puer import Component, Slot, Unit


class ShopConfigs(Configs):
    SHOP_PORT = IntConfig(8080)


class ShopSettingsUnit(SettingsUnit):
    configs = Slot(ShopConfigs)


class ShopServer(Component):
    pass


class ShopUnit(Unit):
    server = Slot(ShopServer)


class RestockCommand(BaseCommand):
    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--mode", dest="restock_mode", choices=("fast", "slow"))

    @t.override
    async def _run(self) -> None:
        pass


class ShopCommandsUnit(CommandsUnit):
    restock = Slot(RestockCommand)


class ShopCliUnit(CliUnit):
    shop = Slot(ShopCommandsUnit)


class ShopProject(Project):
    settings = Slot(ShopSettingsUnit)
    shop = Slot(ShopUnit)
    cli = Slot(ShopCliUnit)


class PlayCommand(BaseCommand):
    @t.override
    async def _run(self) -> None:
        pass


class GameCommandsUnit(CommandsUnit):
    play = Slot(PlayCommand)


class GameCliUnit(CliUnit):
    game = Slot(GameCommandsUnit)


class GameProject(Project):
    cli = Slot(GameCliUnit)


def build(project_cls: type[Project], *target: str) -> str:
    """The script ``completion bash`` prints, the configs off."""
    out = io.StringIO()
    argv = ["--config", "IS_CONFIGURE_LOGGING=off", "completion", "bash", *target]
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        assert CommandRunner(project_cls, argv).run() == 0
    return out.getvalue()


def complete(scripts: t.Sequence[str], line: str, cwd: str = ".") -> list[str]:
    """
    What bash offers at the end of ``line``, an operator pressing Tab, the
    scripts sourced in their order, a completion of another tool among them:
    the words split at the spaces and at ``=``, as bash splits them, and the
    function bound to the program of the line called as bash calls it.
    """
    words = [
        part
        for word in line.split(" ")
        for part in (re.split("(=)", word) if word else [word])
        if part or not word
    ]
    words_bash = " ".join(f"'{word}'" for word in words)
    program = "\n".join(
        [
            *scripts,
            f"COMP_WORDS=({words_bash}); COMP_CWORD={len(words) - 1}",
            # bash looks for the completion of the full path, then of its name
            "cmd=${COMP_WORDS[0]}",
            'spec=$(complete -p -- "$cmd" 2>/dev/null || complete -p -- "${cmd##*/}")',
            'fn=$(sed -E "s/.* -F ([^ ]+) .*/\\1/" <<< "$spec")',
            '"$fn" "$cmd" "${COMP_WORDS[COMP_CWORD]}" "${COMP_WORDS[COMP_CWORD-1]}"',
            "printf '%s\\n' \"${COMPREPLY[@]}\"",
        ]
    )
    result = subprocess.run(
        ["bash", "-c", program], capture_output=True, text=True, cwd=cwd, check=True
    )
    return sorted(filter(None, result.stdout.splitlines()))
