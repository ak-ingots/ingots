# Contributing

Everything goes through `make`; run `make` alone for the target list. It
needs [uv](https://docs.astral.sh/uv/), which fetches the interpreters it
needs.

```sh
make check           # everything CI runs: lint, test, wheel-test, doc, cl-check
make format          # black
make doc             # this documentation into docs/build/ (runs `make apidoc` first)
make doc-serve       # build and serve it on http://127.0.0.1:8000/ [DOC_HOST=0.0.0.0 DOC_PORT=...]
make all             # the sdist and the wheel into dist/
```

## Tests

The suite is stdlib `unittest`. `make test` runs it on the working tree;
`make wheel-test` builds the wheel, installs it into a fresh virtualenv and
runs a copy of `tests/` outside the repository, once per supported Python
(`PYTHONS="3.14 3.15"`), so the package is imported only from the wheel
([ADR 0003](https://github.com/ak-ingots/ingots-libs/blob/main/docs/adr/0003-flat-layout-and-mandatory-library-build.md)).

## Changelog

Every change users should know about adds a news fragment to `changelog.d/`:
`<issue>.<type>.md`, or `+<slug>.<type>.md` without an issue, where the type is
one of `added`, `changed`, `deprecated`, `removed`, `fixed`, `security`.
`make cl-check` (and CI) fails a branch without one; `make cl-build
VERSION=X.Y.Z` collates the fragments into `CHANGELOG.md`.

## Design principles

Code follows the ecosystem's
[design principles](https://github.com/ak-ingots/ingots-libs/blob/main/docs/adr/0006-design-principles.md).
