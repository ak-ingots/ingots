"""
The log context: values of context variables added to every log record, so
an addon puts its request or run id into the logs without a filter of its
own.
"""

__all__ = ("LogContext", "LogContextFilter", "LogContextVar", "get_log_context")

import contextlib
import contextvars
import logging
import typing as t

if t.TYPE_CHECKING:
    from collections.abc import Iterator

_UNSET: t.Final = object()
_NO_DEFAULT: t.Final = object()
_vars: dict[str, "LogContextVar[t.Any]"] = {}


class LogContextVar[ValueType]:
    """
    A context variable whose value, while bound, goes into the log records
    as ``cvars``. Declared once, at the module level, under a name unique in
    the process: an addon prefixes it with its own name.

    Usage::

        REQUEST_ID = LogContextVar[str]("http_request_id")

        with REQUEST_ID.bind(request.uid):
            logger.info("handled")

    An asyncio task copies the context it is created in, so a value bound in
    a task stays in that task.
    """

    def __init__(self, name: str) -> None:
        if name in _vars:
            raise ValueError(f"the log context variable {name!r} is declared already")
        self._name = name
        self._var = contextvars.ContextVar[ValueType](name)
        _vars[name] = self

    @property
    def name(self) -> str:
        """The name the value is logged under."""
        return self._name

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self._name!r})"

    @contextlib.contextmanager
    def bind(self, value: ValueType) -> "Iterator[None]":
        """Sets the value for the block, then restores the previous one."""
        token = self._var.set(value)
        try:
            yield
        finally:
            self._var.reset(token)

    @t.overload
    def get(self) -> ValueType: ...

    @t.overload
    def get[DefaultType](self, default: DefaultType) -> ValueType | DefaultType: ...

    def get(self, default: object = _NO_DEFAULT) -> object:
        """
        The bound value, or ``default`` when none is bound.

        :raises LookupError: no value is bound and no default is given.
        """
        if default is _NO_DEFAULT:
            return self._var.get()
        return self._var.get(default)


class LogContext(dict[str, object]):
    """
    The values bound in the context, by name; formatted as
    ``name=value name=value``, or ``-`` when empty.
    """

    def __str__(self) -> str:
        return " ".join(f"{name}={value}" for name, value in self.items()) or "-"


class LogContextFilter(logging.Filter):
    """Sets ``cvars`` of every record it passes to the bound log context."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.cvars = get_log_context()
        return True


def get_log_context() -> LogContext:
    """The values of the log context variables bound in the current context."""
    context = LogContext()
    for name, var in _vars.items():
        value = var.get(_UNSET)
        if value is not _UNSET:
            context[name] = value
    return context
