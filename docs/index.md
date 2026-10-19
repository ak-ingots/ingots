# Ingots

Statically typed composition of Python applications from reusable addons,
customizable at any depth.

Ingots composes an application from reusable addons, in the spirit of Django's
pluggable apps, but statically: an addon is customized at any depth by plain
subclassing, one short class per level, and the composition is checked twice,
by mypy and when the classes are created. The IDE sees the application's
classes down to the deepest entity, combining addons wrongly fails at import
time rather than in production, and every addon ships contract tests that the
application runs against its own composition.

Ingots is being rewritten from scratch: nothing usable yet.

## Where to go next

- {doc}`concepts/index`: projects, units, entities and slots; the command
  line.
- {doc}`defaults/index`: the standard units: the settings.
- {doc}`reference/index`: the Python API.
- {doc}`contributing`: the development workflow.
- {doc}`changelog`.

```{toctree}
:hidden:
:caption: Concepts

concepts/index
```

```{toctree}
:hidden:
:caption: Defaults

defaults/index
```

```{toctree}
:hidden:
:caption: Reference

reference/index
```

```{toctree}
:hidden:
:caption: Project

contributing
changelog
```
