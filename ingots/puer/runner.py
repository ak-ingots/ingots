"""The runner: drives a project through its life."""

__all__ = ("BaseRunner",)

import abc
import asyncio
import logging
import os
import signal
import typing as t
from collections.abc import Coroutine

if t.TYPE_CHECKING:
    from .project import Project

logger = logging.getLogger(__name__)

STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM)


class BaseRunner:
    """
    Creates a project and runs it in three stages: configures it, runs a
    workflow until the workflow completes or SIGINT/SIGTERM stops it, and
    shuts the project down, whatever happened before. While running, the
    runner is the only long-lived holder of the project; it drops the project
    when done, so the whole tree dies with it.

    Each stop signal insists more than the one before, whatever the stage:

    1. the first asks the workflow to stop and cancels it after the graceful
       timeout; while configuring or shutting down, which cannot be asked,
       it cancels the stage;
    2. the second cancels the current stage at once;
    3. the third kills the process with the signal, as if there were no
       runner.

    A subclass implements the workflow: :meth:`_run_workflow`, and
    :meth:`_stop_workflow` when it can stop without being cancelled. It sets
    ``_debug`` and ``_graceful_timeout`` in :meth:`_prepare_run`.
    """

    GRACEFUL_TIMEOUT_DEFAULT: t.ClassVar[float] = 5.0

    def __init__(self, project_cls: type["Project"]) -> None:
        self._project_cls = project_cls
        self._project: "Project | None" = None
        self._stage_task: "asyncio.Task[t.Any] | None" = None
        self._workflow_task: "asyncio.Task[t.Any] | None" = None
        self._stop_task: "asyncio.Task[None] | None" = None
        self._stop_signals = 0
        self._debug = False
        self._graceful_timeout = self.GRACEFUL_TIMEOUT_DEFAULT

    @property
    def project(self) -> "Project":
        """
        The running project.

        :raises RuntimeError: the runner is not running.
        """
        if self._project is None:
            raise RuntimeError(f"{type(self).__qualname__}: no project is running")
        return self._project

    @t.final
    def run(self) -> int:
        """Runs the project from start to finish and returns the exit code."""
        self._prepare_run()
        return asyncio.run(self._run_project(), debug=self._debug)

    def _prepare_run(self) -> None:
        """
        Prepares the run before the event loop starts: the place to set
        ``_debug`` and ``_graceful_timeout``. Does nothing by default.
        """

    @abc.abstractmethod
    async def _run_workflow(self) -> int:
        """Does the work on the configured project; returns the exit code."""
        raise NotImplementedError(f"{type(self).__qualname__}._run_workflow")

    async def _stop_workflow(self) -> None:
        """
        Asks a running :meth:`_run_workflow` to finish: called on the first
        stop signal. Does nothing here: the workflow is cancelled once the
        graceful timeout is over.
        """

    def _create_project(self) -> "Project":
        """Creates the project to run."""
        return self._project_cls()

    async def _run_project(self) -> int:
        project = self._project = self._create_project()
        loop = asyncio.get_running_loop()
        for sig in STOP_SIGNALS:
            loop.add_signal_handler(sig, self._handle_stop_signal, sig)
        code = 1
        try:
            await self._run_stage("configuring", project._configure())
            code = await self._run_stage(
                "the workflow", self._run_workflow(), is_workflow=True
            )
        except _StageFailed:
            code = 1
        finally:
            try:
                await self._run_stage("shutting down", project._do_shut_down())
            except _StageFailed:
                code = code or 1
            finally:
                for sig in STOP_SIGNALS:
                    loop.remove_signal_handler(sig)
                self._project = self._stop_task = None
                self._stop_signals = 0
        return code

    async def _run_stage[StageResult](
        self,
        name: str,
        stage: Coroutine[t.Any, t.Any, StageResult],
        *,
        is_workflow: bool = False,
    ) -> StageResult:
        task = asyncio.create_task(stage)
        self._stage_task = task
        if is_workflow:
            self._workflow_task = task
        try:
            return await task
        except asyncio.CancelledError:
            current = asyncio.current_task()
            if current is not None and current.cancelling():
                raise  # the run itself is cancelled, not only the stage
            logger.warning("%s was cancelled", name)
            raise _StageFailed(name) from None
        except Exception as error:
            logger.exception("%s failed: %r", name, error)
            raise _StageFailed(name) from None
        finally:
            self._stage_task = self._workflow_task = None

    def _handle_stop_signal(self, sig: signal.Signals) -> None:
        self._stop_signals += 1
        match self._stop_signals:
            case 1 if self._workflow_task is not None:
                logger.info("%s received, stopping", sig.name)
                self._stop_task = asyncio.create_task(
                    self._stop_workflow_gracefully(self._workflow_task)
                )
            case 1 | 2:
                logger.warning("%s received, cancelling", sig.name)
                self._cancel_stage()
            case _:
                logger.warning("%s received a third time, exiting", sig.name)
                self._kill_by_signal(sig)

    async def _stop_workflow_gracefully(self, task: "asyncio.Task[t.Any]") -> None:
        try:
            await self._stop_workflow()
        except Exception as error:
            logger.exception("stopping the workflow failed: %r", error)
        _, pending = await asyncio.wait({task}, timeout=self._graceful_timeout)
        if pending:
            logger.warning("the workflow did not stop in time")
            task.cancel()

    def _cancel_stage(self) -> None:
        if self._stage_task is not None:
            self._stage_task.cancel()

    def _kill_by_signal(self, sig: signal.Signals) -> None:
        # the default action of the signal: the exit status shows the signal
        asyncio.get_running_loop().remove_signal_handler(sig)
        signal.signal(sig, signal.SIG_DFL)
        os.kill(os.getpid(), sig)


class _StageFailed(Exception):
    """A stage of the run failed or was cancelled; it is logged already."""
