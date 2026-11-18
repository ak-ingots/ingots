"""The errors of the load."""

__all__ = ("ScenarioModuleError", "SmokeFailedError")

import typing as t

from ingots.puer import UserError


class ScenarioModuleError(UserError):
    """
    The module of a scenario gives no ``PerfProject`` a run takes: a
    project whose slot ``perf`` is a :class:`~ingots.perf.PerfUnit`. Create
    it with :meth:`for_module`.
    """

    @classmethod
    def for_module(cls, path: str, reason: str) -> t.Self:
        """The error of the module at ``path``, telling why."""
        return cls(f"{path}: {reason}", path)

    @property
    def path(self) -> str:
        """The path of the module."""
        return t.cast(str, self.args[1])

    @t.override
    def __str__(self) -> str:
        return t.cast(str, self.args[0])


class SmokeFailedError(UserError):
    """
    A dry point of ``perf smoke`` found an action that erred, or no action
    measured at all. Create it with :meth:`for_errors`.
    """

    @classmethod
    def for_errors(cls, scenario: str, errors: tuple[str, ...]) -> t.Self:
        """The error of the scenario, its errors ``action: Error``; none, no call."""
        told = ", ".join(errors) if errors else "no action measured"
        return cls(f"{scenario}: {told}", scenario, errors)

    @property
    def scenario(self) -> str:
        """The name of the scenario."""
        return t.cast(str, self.args[1])

    @property
    def errors(self) -> tuple[str, ...]:
        """The errors met, ``action: Error``; none when no action was measured."""
        return t.cast(tuple[str, ...], self.args[2])

    @t.override
    def __str__(self) -> str:
        return t.cast(str, self.args[0])
