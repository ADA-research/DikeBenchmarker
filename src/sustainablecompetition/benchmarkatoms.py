"""Basic benchmarking job and result representation"""

from enum import Enum
from datetime import datetime, timezone


class JobState(Enum):
    """Possible states of a Job."""

    CREATED = 1
    SUBMITTED = 2
    RUNNING = 3
    FINISHED = 4
    FAILED = 5
    CANCELLED = 6


class JobStateError(Exception):
    """Raised when an invalid state transition is attempted on a Job."""


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

    def mark_submitted(self) -> None:
        """
        Mark the job as submitted.
        Called by the infrastructure adapter upon receiving the job.
        """
        if self.state == JobState.SUBMITTED:
            # TODO maybe add a warning message to indicate that job was already submitted
            if self.submitted_at is None:
                self.submitted_at = datetime.now(timezone.utc)
            return
        if self.state != JobState.CREATED:
            raise JobStateError(f"Cannot mark job as SUBMITTED from state {self.state.name}")
        self.state = JobState.SUBMITTED
        self.submitted_at = datetime.now(timezone.utc)

    def mark_running(self) -> None:
        """
        Mark the job as running.
        Called by the infrastructure adapter once the job started to run.
        """
        if self.state == JobState.RUNNING:
            # TODO maybe add a warning message to indicate that job was already submitted
            return
        if self.state != JobState.SUBMITTED:
            raise JobStateError(f"Cannot mark job as RUNNING from state {self.state.name}")
        self.state = JobState.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def set_finished(self) -> None:
        """
        Mark the job as finished.
        Called by the infrastructure adapter when the job has completed successfully.
        """
        if self.state != JobState.RUNNING:
            raise JobStateError(f"Cannot mark job as FINISHED from state {self.state.name}")
        self.state = JobState.FINISHED
        self.finished_at = datetime.now(timezone.utc)

    def set_failed(self, error: str) -> None:
        """
        Mark the job as failed.
        Called by the infrastructure adapter when the job has completed unsuccessfully.
        """
        if self.state != JobState.RUNNING:
            raise JobStateError(f"Cannot mark job as FAILED from state {self.state.name}")
        self.error = error
        self.state = JobState.FAILED
        self.finished_at = datetime.now(timezone.utc)

    def cancel_local(self) -> bool:
        """
        Mark the job as cancelled.
        Called by the benchmarker to prevent the job from being submitted to the external system.
        """
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
