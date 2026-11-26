"""The completion of the command line by bash, built from the classes."""

__all__ = ("BashCompletion", "CompletionKind", "CompletionTarget")

import argparse
import enum
import os
import re
import shlex
import sys
import typing as t
from dataclasses import dataclass

from .data import CliCompletion

if t.TYPE_CHECKING:
    from collections.abc import Iterator

    from ingots.defaults.project import Project

    from .parser import CliTree
    from .runner import CommandRunner


class CompletionKind(enum.Enum):
    """How a program is run, so how bash finds its completion."""

    COMMAND = "command"
    SCRIPT = "script"
    MODULE = "module"


@dataclass(frozen=True, slots=True, kw_only=True)
class CompletionTarget:
    """
    The program completed: a console script by its name, ``shop``; a script
    by its absolute path, ``python manage.py``; a module by its name,
    ``python -m shop``.
    """

    kind: CompletionKind
    name: str

    @classmethod
    def from_argv(cls) -> t.Self:
        """The program run: ``sys.argv[0]``, or the module of ``__main__``."""
        argv0 = sys.argv[0]
        if os.path.basename(argv0) == "__main__.py":
            spec = sys.modules["__main__"].__spec__
            assert spec is not None, "a __main__.py is run as a module"
            return cls(
                kind=CompletionKind.MODULE, name=spec.name.removesuffix(".__main__")
            )
        if argv0.endswith(".py"):
            return cls(kind=CompletionKind.SCRIPT, name=os.path.realpath(argv0))
        return cls(kind=CompletionKind.COMMAND, name=os.path.basename(argv0))


# What every script defines, the same in each, so that the last sourced
# changes nothing. Bash splits the words at "=": they are joined back, so
# that "--mode=fast" is one word. A script, "./manage.py", "python
# manage.py", "uv run manage.py", is found by its absolute path, from the
# directory at hand, a module, "python -m shop", by its name, among those
# registered; for any other, the completion bound to the name before, or
# the one bash-completion loads for it, then the files, by "-o default".
# Bash looks for the completion of the path typed before that of its name:
# a Tab on "./manage.py" before this is sourced leaves the stub of
# bash-completion bound to "./manage.py", which hides ours until removed.
_SHARED = r"""declare -gA _INGOTS_PROGRAMS _INGOTS_PREVIOUS _INGOTS_LOADED
_ingots_join_words() {
    words=() cword=0
    local i w
    for ((i = 0; i < ${#COMP_WORDS[@]}; i++)); do
        w=${COMP_WORDS[i]}
        if ((i > 0)) && [[ ${words[-1]} == -* ]] &&
            [[ $w == = || ${COMP_WORDS[i-1]} == = ]]; then
            words[-1]+=$w
        else
            words+=("$w")
        fi
        ((i == COMP_CWORD)) && cword=$((${#words[@]} - 1))
    done
}
_ingots_bind() {
    local previous
    previous=$(complete -p -- "$1" 2>/dev/null | sed -nE 's/.* -F ([^ ]+) .*/\1/p')
    if [[ -n $previous && $previous != _ingots_* ]]; then
        _INGOTS_PREVIOUS[$1]=$previous
    fi
    complete -o default -F "$2" -- "$1"
}
_ingots_bind_script() {
    local spec name
    while read -r spec; do
        name=${spec##* }
        if [[ $name == */"$1" && $spec == *" -F _comp_complete_minimal "* ]]; then
            complete -r -- "$name"
        fi
    done < <(complete -p)
    _ingots_bind "$1" _ingots_complete_script
}
_ingots_complete_other() {
    local name=$1 fn ours
    shift
    fn=${_INGOTS_PREVIOUS[$name]-}
    if [[ -z $fn && -z ${_INGOTS_LOADED[$name]-} ]]; then
        _INGOTS_LOADED[$name]=1
        ours=$(complete -p -- "$name" 2>/dev/null)
        if declare -F _comp_load >/dev/null; then
            _comp_load -- "$name" 2>/dev/null
        elif declare -F __load_completion >/dev/null; then
            __load_completion "$name" 2>/dev/null
        fi
        fn=$(complete -p -- "$name" 2>/dev/null | sed -nE 's/.* -F ([^ ]+) .*/\1/p')
        [[ $fn == _ingots_* ]] && fn=
        _INGOTS_PREVIOUS[$name]=$fn
        [[ -n $ours ]] && eval "$ours"
    fi
    if [[ -n $fn ]]; then
        "$fn" "$@"
    fi
}
_ingots_find_python() {
    local i=$1
    while [[ ${words[i]-} == -* && ${words[i]} != -m ]]; do
        [[ ${words[i]} == -[XW] ]] && ((i++))
        ((i++))
    done
    if [[ ${words[i]-} == -m ]]; then
        key="-m ${words[i+1]-}" start=$((i + 2))
    elif ((i < cword)); then
        key=$(realpath -q -- "${words[i]}") start=$((i + 1))
    fi
}
_ingots_call() {
    if ((start > 0 && cword >= start)) && [[ -n $key ]] &&
        [[ -n ${_INGOTS_PROGRAMS[$key]-} ]]; then
        "${_INGOTS_PROGRAMS[$key]}" "$start"
        return 0
    fi
    return 1
}
_ingots_complete_python() {
    local words cword key= start=0
    _ingots_join_words
    _ingots_find_python 1
    _ingots_call || _ingots_complete_other "${1##*/}" "$@"
}
_ingots_complete_uv() {
    local words cword key= start=0 i=2
    _ingots_join_words
    if [[ ${words[1]-} == run ]]; then
        while [[ ${words[i]-} == -* && ${words[i]} != -m ]]; do
            case ${words[i]} in
                --with | --with-editable | --with-requirements | --python | -p | \
                    --project | --directory | --package | --extra | --group | \
                    --only-group | --no-group | --env-file | --index | \
                    --default-index | --index-url | --extra-index-url | \
                    --find-links | -f | --config-file | --cache-dir | --color)
                    ((i++)) ;;
            esac
            ((i++))
        done
        [[ ${words[i]-} == python || ${words[i]-} == python3 ]] && ((i++))
        _ingots_find_python "$i"
    fi
    _ingots_call || _ingots_complete_other uv "$@"
}
_ingots_complete_script() {
    local words cword key= start=1
    _ingots_join_words
    if [[ ${words[0]} == */* ]]; then
        key=$(realpath -q -- "${words[0]}")
    else
        key=$(realpath -q -- "$(type -P -- "${words[0]}")")
    fi
    _ingots_call || _ingots_complete_other "${1##*/}" "$@"
}"""

# The completion of one program: the words after the program walked from
# the root, a sub-command moving to its node, an option taking a value
# skipping it; then the value of an option before the word, or after its
# "=", else the options and the sub-commands of the node.
_PROGRAM = r"""{function}() {{
    local start=$1 words cword node= i word option value cur
    _ingots_join_words
    cur=${{words[cword]}}
    for ((i = start; i < cword; i++)); do
        word=${{words[i]}}
        [[ $word == -*=* ]] && continue
        case "$node|$word" in
{walk}
        esac
    done
    if [[ $cur == -*=* ]]; then
        option=${{cur%%=*}} value=${{cur#*=}}
    else
        option=${{words[cword-1]}} value=$cur
    fi
    COMPREPLY=()
    case "$node|$option" in
{values}
    esac
    case "$node" in
{words}
    esac
}}"""


class BashCompletion:
    """
    The script of the completion of bash for a program of a project, built
    from the classes of its command line as the runner builds it: no Python
    runs on Tab. Each node completes its sub-commands and its options, the
    root those of the runner too; an option taking a value completes it by
    the hook of its node, :meth:`~ingots.defaults.cli.CliNode._cli_complete`,
    or by its ``choices``.
    """

    def __init__(
        self,
        project_cls: "type[Project]",
        runner_cls: "type[CommandRunner]",
        target: CompletionTarget,
    ) -> None:
        self._project_cls = project_cls
        self._runner_cls = runner_cls
        self._target = target
        # the prefix keeps it off the functions of other tools
        name = re.sub(r"\W", "_", target.name)
        self._function = f"_ingots_{target.kind.value}_{name}_complete"

    def build(self) -> str:
        """The script, sourced by bash."""
        tree = self._runner_cls.cli_parser_cls(self._project_cls, self._runner_cls).tree
        nodes = list(self._iter_nodes(tree))
        walk = [
            f'            "{_get_key(node)}|{child.name}") node={_get_key(child)} ;;'
            for node, _ in nodes
            for child in node.children
        ] + [
            f'            "{_get_key(node)}|{option}") ((i++)) ;;'
            for node, parser in nodes
            for action in _iter_valued(parser)
            for option in action.option_strings
        ]
        values = [
            f'        "{_get_key(node)}|{option}") {self._get_reply(completion)}'
            "; return ;;"
            for node, parser in nodes
            for action in _iter_valued(parser)
            if (completion := self._get_completion(node, action)) != CliCompletion()
            for option in action.option_strings
        ]
        words = [
            f'        "{_get_key(node)}") COMPREPLY=($(compgen -W '
            f"{shlex.quote(' '.join(_get_words(node, parser)))} -- \"$cur\")) ;;"
            for node, parser in nodes
        ]
        program = _PROGRAM.format(
            function=self._function,
            walk="\n".join(walk),
            values="\n".join(values),
            words="\n".join(words),
        )
        return "\n".join([_SHARED, program, *self._get_binding(), ""])

    def _iter_nodes(
        self, tree: "CliTree"
    ) -> "Iterator[tuple[CliTree, argparse.ArgumentParser]]":
        parser = argparse.ArgumentParser(add_help=False)
        if not tree.path:
            self._runner_cls._cli_prepare_parser(parser)
        tree.cls._cli_prepare_parser(parser)
        yield tree, parser
        for child in tree.children:
            yield from self._iter_nodes(child)

    def _get_completion(
        self, node: "CliTree", action: argparse.Action
    ) -> CliCompletion:
        completion = node.cls._cli_complete(self._project_cls, action.dest)
        if completion == CliCompletion() and action.choices:
            return CliCompletion(words=tuple(map(str, action.choices)))
        return completion

    def _get_reply(self, completion: CliCompletion) -> str:
        if completion.files:
            return 'COMPREPLY=($(compgen -f -- "$value"))'
        words = shlex.quote(" ".join(completion.words))
        reply = f'COMPREPLY=($(compgen -W {words} -- "$value"))'
        if not completion.is_spaced:
            reply += "; compopt -o nospace 2>/dev/null"
        return reply

    def _get_binding(self) -> list[str]:
        target = self._target
        if target.kind is CompletionKind.COMMAND:
            return [
                f"{self._function}_bound() {{ {self._function} 1; }}",
                f"complete -F {self._function}_bound {shlex.quote(target.name)}",
            ]
        key = target.name
        if target.kind is CompletionKind.MODULE:
            key = f"-m {target.name}"
        binding = [
            f"_INGOTS_PROGRAMS[{shlex.quote(key)}]={self._function}",
            "_ingots_bind python _ingots_complete_python",
            "_ingots_bind python3 _ingots_complete_python",
            "_ingots_bind uv _ingots_complete_uv",
        ]
        if target.kind is CompletionKind.SCRIPT:
            name = shlex.quote(os.path.basename(target.name))
            binding.append(f"_ingots_bind_script {name}")
        return binding


def _get_key(node: "CliTree") -> str:
    return ".".join(node.path)


def _iter_valued(parser: argparse.ArgumentParser) -> "Iterator[argparse.Action]":
    # argparse keeps its actions under a private name, read by argcomplete
    # too; the tests run the script under bash, so a change shows
    for action in parser._actions:
        if action.option_strings and action.nargs != 0:
            yield action


def _get_words(node: "CliTree", parser: argparse.ArgumentParser) -> list[str]:
    options = [option for action in parser._actions for option in action.option_strings]
    return [*options, *(child.name for child in node.children)]
