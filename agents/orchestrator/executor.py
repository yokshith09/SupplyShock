"""DAG executor: dependency order, parallel ready tasks, timeout + retries, fallback/degraded mode,
re-plan hook, HUMAN approval gate with pause/resume.

Status: PLANNED -> RUNNING -> AWAITING_APPROVAL -> RUNNING -> CLOSED | DEGRADED | FAILED
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from agents.orchestrator.planner import Plan, Task, validate_plan
from shared.logging import get_logger, log_task
from shared.models import TaskError

log = get_logger("executor")


class TaskFailed(Exception):
    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class HaltPlan(Exception):
    """Raised by a task runner to stop the plan cleanly with a message for the user."""


@dataclass
class DagRun:
    plan: Plan
    run_task: Callable[[Task, dict], Awaitable[Any]]
    fallback: Callable[[Task, dict, Exception], Any] | None = None
    replan: Callable[[Task, Any], list[Task] | None] | None = None
    on_result: Callable[[Task, Any], None] | None = None
    incident_id: str = ""
    timeout_s: float = 20.0
    retries: int = 2
    backoff_s: tuple = (1.0, 3.0)
    results: dict = field(default_factory=dict)
    errors: dict = field(default_factory=dict)
    degraded: list = field(default_factory=list)
    status: str = "PLANNED"
    halt_message: str = ""
    pending_human: Task | None = None
    _done: set = field(default_factory=set)
    _failed: set = field(default_factory=set)
    _skipped: set = field(default_factory=set)
    _halted: bool = False

    # ---- scheduling -------------------------------------------------------------------
    def _remaining(self) -> list[Task]:
        gone = self._done | self._failed | self._skipped
        return [t for t in self.plan.tasks if t.id not in gone]

    def _skip_blocked(self) -> None:
        changed = True
        while changed:
            changed = False
            bad = self._failed | self._skipped
            for t in self._remaining():
                if any(d in bad for d in t.depends_on):
                    self._skipped.add(t.id)
                    changed = True

    def _ready(self) -> list[Task]:
        self._skip_blocked()
        return [t for t in self._remaining() if all(d in self._done for d in t.depends_on)]

    async def run(self) -> "DagRun":
        self.status = "RUNNING"
        while not self._halted:
            ready = self._ready()
            if not ready:
                break
            normal = [t for t in ready if t.agent != "human"]
            if normal:
                await asyncio.gather(*(self._exec(t) for t in normal))
                continue
            self.pending_human = ready[0]
            self.status = "AWAITING_APPROVAL"
            return self
        self._finish()
        return self

    async def resume(self, approved: bool) -> "DagRun":
        t = self.pending_human
        if t is None:
            return self
        self.pending_human = None
        self.results[t.id] = {"approved": approved}
        self._done.add(t.id)
        if not approved:
            self._skipped.update(x.id for x in self._remaining())
            self.halt_message = "Not approved. No actions were taken."
            self.status = "CLOSED"
            return self
        return await self.run()

    def _finish(self) -> None:
        if self._halted:
            self.status = "CLOSED"
        elif self._failed:
            self.status = "FAILED"
        elif self.degraded:
            self.status = "DEGRADED"
        else:
            self.status = "CLOSED"

    # ---- one task ---------------------------------------------------------------------
    async def _exec(self, task: Task) -> None:
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            t0 = time.perf_counter()
            try:
                res = await asyncio.wait_for(self.run_task(task, self.results), self.timeout_s)
                if isinstance(res, TaskError):
                    raise TaskFailed(res.message, res.retryable)
            except HaltPlan as e:
                self.halt_message, self._halted = str(e), True
                self._done.add(task.id)
                self._skipped.update(x.id for x in self._remaining())
                log_task(log, f"halt: {e}", incident_id=self.incident_id, task_id=task.id,
                         agent=task.agent, status="halt")
                return
            except Exception as e:  # noqa: BLE001 - every failure goes through retry/fallback
                last = e
                retryable = getattr(e, "retryable", True)
                log_task(log, f"attempt {attempt + 1} failed: {e!r}", incident_id=self.incident_id,
                         task_id=task.id, agent=task.agent, level=logging.WARNING, status="retry",
                         latency_ms=int((time.perf_counter() - t0) * 1000))
                if not retryable or attempt == self.retries:
                    break
                await asyncio.sleep(self.backoff_s[min(attempt, len(self.backoff_s) - 1)])
                continue
            self._record(task, res, t0)
            return
        fb = self.fallback(task, self.results, last) if (self.fallback and last) else None
        if fb is not None:
            self.degraded.append(task.id)
            self._record(task, fb, time.perf_counter(), status="degraded")
        else:
            self._failed.add(task.id)
            self.errors[task.id] = repr(last)
            log_task(log, f"failed: {last!r}", incident_id=self.incident_id, task_id=task.id,
                     agent=task.agent, level=logging.ERROR, status="failed")

    def _record(self, task: Task, res: Any, t0: float, status: str = "ok") -> None:
        self.results[task.id] = res
        self._done.add(task.id)
        if getattr(res, "degraded", False) and task.id not in self.degraded:
            self.degraded.append(task.id)
        log_task(log, f"{task.agent}.{task.action} {status}", incident_id=self.incident_id,
                 task_id=task.id, agent=task.agent, status=status,
                 latency_ms=int((time.perf_counter() - t0) * 1000))
        if self.on_result:
            self.on_result(task, res)
        if self.replan:
            new = self.replan(task, res)
            if new:
                self.plan = validate_plan(Plan(intent=self.plan.intent, tasks=self.plan.tasks + new))
