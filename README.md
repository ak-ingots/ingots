# Ingots

[![ci](https://github.com/ak-ingots/ingots/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ak-ingots/ingots/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/ak-ingots/ingots/blob/main/LICENSE)
[![Documentation Status](https://app.readthedocs.org/projects/ingots/badge/?version=latest)](https://ingots.readthedocs.io/en/latest/)

<!-- Links must be absolute: this README also renders on PyPI. -->

Statically typed composition of Python applications from reusable addons,
customizable at any depth.

Ingots composes an application from reusable addons, in the spirit of Django's
pluggable apps, but statically: an addon is customized at any depth by plain
subclassing, one short class per level, and the composition is checked twice,
by mypy and when the classes are created. The IDE sees the application's
classes down to the deepest entity, combining addons wrongly fails at import
time rather than in production, and every addon ships contract tests that the
application runs against its own composition.

**Status:** alpha. The core is in place: projects, units, entities and typed
slots, the command-line runner and the components, with the standard units for
the settings and the logging. The API may still change between minor versions.

## Development

Requires [uv](https://docs.astral.sh/uv/) and `make`; uv fetches the
interpreters it needs.

```sh
make                 # the target list
make check           # everything CI runs: lint, test, wheel-test, doc, cl-check
make format          # black
make doc             # the documentation into docs/build/ (runs `make apidoc` first)
make doc-serve       # build and serve it on port 8000 of every interface [DOC_HOST=127.0.0.1 DOC_PORT=...]
make all             # build the sdist and the wheel into dist/
```

- `make test` runs the suite (stdlib `unittest`) on the working tree;
  `make wheel-test` runs it on the built wheel for every supported Python
  (`PYTHONS="3.14 3.15"`).
- Every change users should know about adds a news fragment to `changelog.d/`
  (see [its README](https://github.com/ak-ingots/ingots/blob/main/changelog.d/README.md));
  `make cl-check` fails a branch without one.
