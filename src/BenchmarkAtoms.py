from enum import Enum
from datetime import datetime, timezone


class JobState(Enum):
    CREATED = 1
    SUBMITTED = 2
    RUNNING = 3
    FINISHED = 4
    FAILED = 5
    CANCELLED = 6


class JobStateError(Exception):
    """Raised when an invalid state transition is attempted on a Job."""

    pass


class Job:
    """
    Benchmarking Job that behaves like a future.

    Identity: benchmark_id, solver_id, created_at (ctor time).
    Lifecycle:
      CREATED (initial)
        --[put into JobLog]--> SUBMITTED
        --[start working on]--> RUNNING
        --[finish working on]--> FINISHED | FAILED
      CREATED/SUBMITTED -> CANCELLED
    """

    def __init__(self, benchmark_id: str, solver_id: str, tlimit: int = 5000, mlimit: int = 30) -> None:
        self.benchmark_id: str = benchmark_id
        self.solver_id: str = solver_id
        self.timelimit: int = tlimit  # seconds
        self.memlimit: int = mlimit  # gigabytes

        # timestamps
        self.created_at: datetime = datetime.now(timezone.utc)
        self.submitted_at: datetime | None = None
        self.started_at: datetime | None = None
        self.finished_at: datetime | None = None

        # state data
        self.state: JobState = JobState.CREATED
        self.result: Result | None = None
        self.error: str | None = None

        # set by worker when submitted to external system
        self.external_id: str | None = None

    # ---- called by submitter when enqueuing ----
    def mark_submitted(self) -> None:
        if self.state != JobState.CREATED:
            raise JobStateError(f"Cannot mark job as SUBMITTED from state {self.state.name}")
        self.state = JobState.SUBMITTED
        self.submitted_at = datetime.now(timezone.utc)

    # ---- called by worker when handing off to external system ----
    async def mark_running(self) -> None:
        if self.state != JobState.SUBMITTED:
            raise JobStateError(f"Cannot mark job as RUNNING from state {self.state.name}")
        self.state = JobState.RUNNING
        self.started_at = datetime.now(timezone.utc)

    # ---- called by worker when finishing the job ----
    async def set_finished(self) -> None:
        if self.state != JobState.RUNNING:
            raise JobStateError(f"Cannot mark job as FINISHED from state {self.state.name}")
        self.state = JobState.FINISHED
        self.finished_at = datetime.now(timezone.utc)

    async def set_failed(self, error: str) -> None:
        if self.state != JobState.RUNNING:
            raise JobStateError(f"Cannot mark job as FAILED from state {self.state.name}")
        self.error = error
        self.state = JobState.FAILED
        self.finished_at = datetime.now(timezone.utc)

    async def cancel_local(self) -> bool:
        if self.state in (JobState.CREATED, JobState.SUBMITTED):
            self.state = JobState.CANCELLED
            self.finished_at = datetime.now(timezone.utc)
            return True
        return False

    def __repr__(self) -> str:
        return f"Job({self.benchmark_id!r}, {self.solver_id!r}, {self.state.name})"


class Result:
    """
    Represents the result of a benchmark job.
    Contains a reference to the job and its resource usage.
    """

    def __init__(self, job: Job, runtime=None, memory=None):
        self.job = job
        self.runtime = runtime
        self.memory = memory

    def __repr__(self):
        return f"BenchmarkResult(cputime={self.runtime}, memory={self.memory})"
