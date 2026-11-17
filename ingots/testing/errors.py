"""The errors of the testing."""

__all__ = ("OutsideRunError", "TestsFailedError")

import typing as t

from ingots.puer import UserError


class TestsFailedError(UserError):
    """
    Tests of ``testing run`` failed: the command exits with 1, the run of
    unittest told which above. Create it with :meth:`for_counts`.
    """

    @classmethod
    def for_counts(cls, failed: int, run: int) -> t.Self:
        """The error of ``failed`` tests of ``run``."""
        return cls(f"{failed} of {run} tests failed", failed, run)

    @property
    def failed(self) -> int:
        """The tests failed, errors included."""
        return t.cast(int, self.args[1])

    @property
    def run(self) -> int:
        """The tests run."""
        return t.cast(int, self.args[2])

    @t.override
    def __str__(self) -> str:
        return t.cast(str, self.args[0])


class OutsideRunError(Exception):
    """
    A fixture of a :class:`~ingots.testing.TestingProject` read outside its
    ``testing run``: its tests run by the command only, configured as it is.
    Create it with :meth:`for_package`.
    """

    @classmethod
    def for_package(cls, package: str) -> t.Self:
        """The error of the tests of ``package``, telling the command."""
        return cls(f"run by: python -m {package} testing run", package)

    @property
    def package(self) -> str:
        """The package of the project, run by ``python -m``."""
        return t.cast(str, self.args[1])

    @t.override
    def __str__(self) -> str:
        return t.cast(str, self.args[0])
