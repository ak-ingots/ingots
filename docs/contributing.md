# Contributing

Everything goes through `make`; run `make` alone for the target list. It
needs [uv](https://docs.astral.sh/uv/), which fetches the interpreters it
needs.

```sh
make check           # everything CI runs: lint, test, wheel-test, doc, cl-check
make format          # black
make doc             # this documentation into docs/build/ (runs `make apidoc` first)
make doc-serve       # build and serve it on port 8000 of every interface [DOC_HOST=127.0.0.1 DOC_PORT=...]
make all             # the sdist and the wheel into dist/
```

## Tests

The suite is stdlib `unittest`. `make test` runs it on the working tree,
`make coverage` the same under coverage.py, failing below 99% of lines and
branches (`if t.TYPE_CHECKING:` blocks and `raise NotImplementedError` are
left out);
`make wheel-test` builds the wheel, installs it into a fresh virtualenv and
runs a copy of `tests/` outside the repository, once per supported Python
(`PYTHONS="3.14 3.15"`), so the package is imported only from the wheel
([ADR 0003](https://github.com/ak-ingots/ingots-libs/blob/main/docs/adr/0003-flat-layout-and-mandatory-library-build.md)).

`INGOTS_TEST_LOG=<level>` shows the logs of the run, e.g.
`INGOTS_TEST_LOG=info make test`; test cases derived from `tests.TestCase`
show the logs they capture with `assertLogs` too.

## Changelog

Every change users should know about adds a news fragment to `changelog.d/`:
`<issue>.<type>.md`, or `+<slug>.<type>.md` without an issue, where the type is
one of `added`, `changed`, `deprecated`, `removed`, `fixed`, `security`.
`make cl-check` (and CI) fails a branch without one; `make cl-build
VERSION=X.Y.Z` collates the fragments into `CHANGELOG.md`.

## Releasing

A release is a pull request and a tag:

1. The release pull request sets the version, `uv version X.Y.Z`, and
   collates the changelog, `make cl-build VERSION=X.Y.Z`.
2. Once it is merged, the tag `vX.Y.Z` on its commit in `main` starts the
   `release` workflow: it checks the tag against the version, runs
   `make wheel-test` and publishes the tested build to TestPyPI. Then
   `make index-test` installs the package as TestPyPI gives it, its
   dependencies from PyPI, checks it is the same file as the build and runs
   the tests on it for every supported Python; only then does the workflow
   publish the build to PyPI, through trusted publishing.
3. The next pull request moves `main` on to the next development version,
   `uv version X.Y.(Z+1).dev0`.

Run by hand, the `release` workflow rehearses on TestPyPI only, as
`X.Y.Z.devN` with `N` the run number. A version is published once: neither
index takes it again, even after a deletion.

## Design principles

Code follows the ecosystem's
[design principles](https://github.com/ak-ingots/ingots-libs/blob/main/docs/adr/0006-design-principles.md).
