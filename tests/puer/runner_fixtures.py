"""
Runners without a command line: workflows that finish, fail, stop when asked,
ignore stopping, survive cancelling; and projects that hang or fail while
configuring and shutting down.
"""

import asyncio
import os
import signal
import weakref

from ingots.puer import BaseRunner, Project

# what happened during a run: the project is gone when the run returns
EVENTS: list[str] = []
PROJECTS: list[weakref.ref["RecordingProject"]] = []


class RecordingProject(Project):
    async def configure(self) -> None:
        PROJECTS.append(weakref.ref(self))
        EVENTS.append("configure")

    async def shut_down(self) -> None:
        EVENTS.append("shut down")


class HangingProject(RecordingProject):
    """Hangs while configuring and shutting down, until a signal cancels it."""

    async def configure(self) -> None:
        await super().configure()
        await hang_until_cancelled("configure")

    async def shut_down(self) -> None:
        await super().shut_down()
        await hang_until_cancelled("shut down")


class FailingShutDownProject(RecordingProject):
    async def shut_down(self) -> None:
        await super().shut_down()
        raise RuntimeError("boom")


class RecordingRunner(BaseRunner):
    """Works and exits with :attr:`code`; records whether the loop debugs."""

    code = 0

    def __init__(self, project_cls: type[Project] = RecordingProject) -> None:
        super().__init__(project_cls)

    async def run_workflow(self) -> int:
        debug = asyncio.get_running_loop().get_debug()
        EVENTS.append(f"work, debug={debug}")
        return self.code


class DebugRunner(RecordingRunner):
    def __init__(self) -> None:
        super().__init__()
        self._debug = True


class ExitingRunner(RecordingRunner):
    code = 3


class FailingRunner(RecordingRunner):
    async def run_workflow(self) -> int:
        raise RuntimeError("boom")


class ServingRunner(RecordingRunner):
    """Runs until stopped: sends itself SIGINT once it is serving."""

    def __init__(self) -> None:
        super().__init__()
        self._stopped = asyncio.Event()

    async def run_workflow(self) -> int:
        EVENTS.append("serving")
        asyncio.get_running_loop().create_task(send_signals(signal.SIGINT))
        await self._stopped.wait()
        EVENTS.append("served")
        return 0

    async def stop_workflow(self) -> None:
        EVENTS.append("stop")
        self._stopped.set()


class StubbornRunner(RecordingRunner):
    """
    Ignores stopping, keeping the default :meth:`stop_workflow`: the runner
    cancels it once the graceful timeout is over.
    """

    signals = 1

    def __init__(self) -> None:
        super().__init__()
        self._graceful_timeout = 0.05

    async def run_workflow(self) -> int:
        asyncio.get_running_loop().create_task(
            send_signals(signal.SIGTERM, self.signals)
        )
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            EVENTS.append("cancelled")
            raise
        return 0


class BrokenStopRunner(StubbornRunner):
    """Fails to stop: the runner still cancels it after the graceful timeout."""

    async def stop_workflow(self) -> None:
        raise RuntimeError("boom")


class ObstinateRunner(StubbornRunner):
    """Gets a second signal long before the graceful timeout is over."""

    signals = 2

    def __init__(self) -> None:
        super().__init__()
        self._graceful_timeout = 3600


class UnkillableRunner(ObstinateRunner):
    """Survives cancelling: only the third signal ends it."""

    signals = 3

    async def run_workflow(self) -> int:
        try:
            return await super().run_workflow()
        except asyncio.CancelledError:
            await asyncio.sleep(3600)
            return 0


async def hang_until_cancelled(stage: str) -> None:
    asyncio.get_running_loop().create_task(send_signals(signal.SIGTERM))
    try:
        await asyncio.sleep(3600)
    except asyncio.CancelledError:
        EVENTS.append(f"{stage} cancelled")
        raise


async def send_signals(sig: signal.Signals, count: int = 1) -> None:
    for _ in range(count):
        os.kill(os.getpid(), sig)
        await asyncio.sleep(0.01)
