# CLAUDE.md

Guidance for Claude Code in this repository. Keep it under 200 lines and do not
repeat what README, `docs/` or the ADRs say: link to them.

## What this is

`ingots`: statically typed composition of Python applications from reusable
addons. Rewritten from scratch since 0.30.0: the PUER core, the command line,
the components and the defaults (settings, logging). A library (ADR 0003),
Python >= 3.14, part of the [ak-ingots](https://github.com/ak-ingots)
ecosystem; the meta repository
`ingots-libs` holds the ecosystem-wide decisions in `docs/adr/`.

## Commands

Everything goes through `make` (run `make` alone for the target list); uv
provides the environments and interpreters.

```bash
make check        # what CI runs: lint, test, coverage, wheel-test, doc, cl-check
make lint         # black --check, flake8, mypy --strict
make test         # unittest on the working tree
make coverage     # the same under coverage; fails below 99%
make wheel-test   # unittest on the built wheel, PYTHONS="3.14 3.15"
make format       # black
make doc          # apidoc, then Sphinx; warnings are errors
make doc-serve    # doc, then serve docs/build/ [DOC_HOST=0.0.0.0 DOC_PORT=8000]
```

One test: `uv run python -m unittest tests.test_canary.CanaryTestCase`.
Logs of a run: `INGOTS_TEST_LOG=info make test` (test cases derive from
`tests.TestCase` to show what `assertLogs` captures too).

## Commits and GitHub

- Never commit, amend, push, open a pull request, tag or rewrite history on
  your own initiative: show a summary and the proposed message, wait for an
  explicit approval of that commit. One approval does not extend to the
  next. Never merge a pull request: the user does (`gh pr merge` is denied).
- The remote is `ak-ingots/ingots`. Inside the `ingots-libs` checkout, run gh
  and git network commands as `direnv exec /home/bee/work/ingots-libs <cmd>`
  (the token comes from its `.envrc`; never read it). Release tags are
  `vX.Y.Z`, the version is bumped with `uv version --bump`.
- `main` and `release/X.Y` are protected by a ruleset: no direct push, force
  push or deletion; pull requests only, squash-merged, with every CI job
  green on a branch up to date with `main`. One change per branch and PR,
  kept to one commit; the squash commit takes the PR title and description,
  so write them as the commit message. The `Co-Authored-By` trailer goes in
  the branch commit only: GitHub carries it to the end of the squash commit.
- Before pushing a branch, rebase it onto the current `main` and run
  `make check`. After the user merges, switch to `main`, pull and delete the
  local branch.

## Rules

- Every change users should know about adds a fragment to `changelog.d/`
  (`<issue>.<type>.md` or `+<slug>.<type>.md`, see `changelog.d/README.md`);
  `cl-check` fails CI without one.
- The version is static in `pyproject.toml` (`uv_build`, no setuptools-scm);
  it changes only at release time.
- Flat layout: the package is `ingots/` at the root. The wheel must be
  complete: `make wheel-test` imports the package only from the wheel.
- Tests are stdlib `unittest`, no pytest. Code passes `mypy --strict` with
  `explicit-override`: every override takes `@t.override`; black at 88
  columns.
- The supported interpreters are listed in three places with nothing linking
  them: `PYTHONS` in the Makefile, the classifiers and the `wheel` matrix in
  `.github/workflows/ci.yml`. Change them together.
- CI runs exactly the `make` targets; a new check goes into `make check` and
  `ci.yml` together.
- Code layout and naming follow ADR 0007: class members and module contents
  top-down, verbs for methods, `Base` only for incomplete classes
  (`@abc.abstractmethod`, no `ABC`), mixin members under the mixin's prefix
  (`_slots_get_project`), module functions for services on a class, type
  parameters named after what fills them. `flake8-class-attributes-order`
  checks the member order; `__init_subclass__` takes an explicit
  `@classmethod`.

## Design

Composition follows ADR 0004 (static composition with typed slots; the
dynamic and generics-based designs were rejected, do not propose them again),
contract tests ADR 0005, design principles ADR 0006. The prototypes behind ADR
0004 are in `ingots-libs/docs/design/extension-composition/`. The previous
implementation (cloned as `ingots-libs/ingots-current/` when present) is a
reference for the runner, CLI and defaults, not for composition.
