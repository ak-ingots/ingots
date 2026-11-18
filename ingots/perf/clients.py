"""The clients of the load and their groups."""

__all__ = ("Call", "LoadClient", "LoadGroup", "Recorder")

import abc
import contextlib
import dataclasses
import time
import typing as t
import weakref

if t.TYPE_CHECKING:
    from collections.abc import AsyncIterator, MutableSequence

    from ingots.puer import Project


@dataclasses.dataclass(frozen=True, slots=True)
class Call:
    """A call measured: its action, its latency in seconds, its error if any."""

    action: str
    latency: float
    error: str = ""


class Recorder:
    """
    The calls of a point ending in its measured window, ``start`` to
    ``end``, seconds of the epoch, as every process of the point keeps them.
    """

    def __init__(self, start: float, end: float) -> None:
        self.start = start
        self.end = end
        self.calls: "MutableSequence[Call]" = []

    def record(self, action: str, begun: float, done: float, error: str = "") -> None:
        """Keeps a call begun and done in the window."""
        if begun >= self.start and done <= self.end:
            self.calls.append(Call(action, done - begun, error))


class LoadGroup[RowType]:
    """
    The clients that meet in a point, one of each class of :attr:`clients`,
    a class twice for two, and what they share: the row of the seed the
    group takes, :attr:`seeded`, a time one starts and another finishes,
    the state a subclass declares, set up by :meth:`asyncSetUp`. An instance
    a group of a point, its clients in one process of the load.
    """

    clients: tuple[type["LoadClient[t.Any, t.Self]"], ...] = ()

    def __init__(self, seeded: RowType, recorder: Recorder) -> None:
        self.seeded = seeded
        self._recorder = recorder
        self._started: dict[tuple[str, str], float] = {}

    async def asyncSetUp(self) -> None:
        """Sets the group up before its clients, unmeasured. Nothing by default."""

    def start(self, action: str, key: str) -> None:
        """Starts the time of an action another client of the group finishes."""
        self._started[action, key] = time.time()

    def finish(self, action: str, key: str) -> None:
        """
        Finishes the time of an action started by :meth:`start`, measured.

        :raises KeyError: no client of the group started it.
        """
        begun = self._started.pop((action, key))
        self._recorder.record(action, begun, time.time())


class LoadClient[ProjectType: "Project", GroupType: LoadGroup[t.Any]](abc.ABC):
    """
    A user of the application, an instance a client of a point: its
    :meth:`asyncSetUp` unmeasured, then its :meth:`run` again and again until
    the window of the point is over, what it measures named by it,
    ``async with self.measure("get-own-profile")``. ``ProjectType`` is the
    ``PerfProject`` of the scenario, ``GroupType`` its group.
    """

    def __init__(self, project: ProjectType, group: GroupType) -> None:
        self._project = weakref.ref(project)
        self.group = group

    @property
    def project(self) -> ProjectType:
        """
        The project of the scenario, for immediate use.

        :raises ReferenceError: the project is gone.
        """
        project = self._project()
        if project is None:
            raise ReferenceError(f"{type(self).__qualname__}: the project is gone")
        return project

    async def asyncSetUp(self) -> None:
        """Sets the client up, unmeasured. Nothing by default."""

    @abc.abstractmethod
    async def run(self) -> None:
        """A pass of the client, again and again; it measures what it calls."""
        raise NotImplementedError(f"{type(self).__qualname__}.run")

    @contextlib.asynccontextmanager
    async def measure(self, action: str) -> "AsyncIterator[None]":
        """
        Measures the block as the action: its latency, or its error by the
        name of its class, which the block does not raise further, so that the
        client goes on.
        """
        recorder = self.group._recorder
        begun = time.time()
        try:
            yield
        except Exception as error:
            recorder.record(action, begun, time.time(), type(error).__qualname__)
        else:
            recorder.record(action, begun, time.time())
